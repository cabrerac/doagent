"""Tests for the Werewolf outcome line and the level 2 explanation."""

from __future__ import annotations

import unittest

from experiments.multiagentbench.run_werewolf_doagent import (
    assign_roles,
    play,
    write_cost,
    write_run_artifacts,
)
from experiments.multiagentbench.truth import read_truth
from experiments.multiagentbench.werewolf_doagent import WerewolfEnv, _speech_order
from experiments.multiagentbench.werewolf_player import fill_prompt, load_prompt
from experiments.multiagentbench.werewolf_session import lines_for

ROLES = {"Lacy": "wolf", "John": "wolf", "Ethel": "villager"}


def _complete(messages, tools):
    del messages
    name = tools[0]["function"]["name"]
    if name in ("werewolf_action", "werewolf_consensus_action"):
        return {
            "action": {"attack": True, "target": "Ethel"},
            "explanation": "because Ethel",
        }
    return {
        "action": {"run_for_sheriff": False, "action_vote": "abstain", "speech": "day"},
        "explanation": "because Ethel",
    }


class RoleTests(unittest.TestCase):
    def test_published_config_assigns_nine_roles(self) -> None:
        roles = assign_roles(seed=1)
        self.assertEqual(len(roles), 9)
        self.assertEqual(list(roles.values()).count("wolf"), 3)
        self.assertEqual(list(roles.values()).count("villager"), 3)
        self.assertEqual(list(roles.values()).count("seer"), 1)

    def test_artifacts_come_from_the_session(self) -> None:
        import tempfile
        from pathlib import Path

        session = play(ROLES, 0, _complete)
        try:
            directory = Path(tempfile.mkdtemp())
            write_run_artifacts(session, ROLES, directory)
            self.assertTrue((directory / "truth.json").is_file())
            self.assertTrue((directory / "gap.json").is_file())
            (directory / "note.txt").write_text("run", encoding="utf-8")
            write_cost(directory, 1.5, None)
            import json

            cost = json.loads((directory / "cost.json").read_text(encoding="utf-8"))
            self.assertGreater(cost["file_count"], 0)
            self.assertGreater(cost["storage_bytes"], 0)
            self.assertIsNone(cost["tokens"])
            self.assertEqual(cost["wall_seconds"], 1.5)
        finally:
            session.close()


class SpeechOrderTests(unittest.TestCase):
    def test_sheriff_speaks_last(self) -> None:
        order = _speech_order(
            ["John", "Lacy", "Mary"],
            ["John", "Lacy", "Mary"],
            "Mary",
            "Lacy",
            True,
        )
        self.assertEqual(order, ["Lacy", "John", "Mary"])
        self.assertEqual(order[-1], "Mary")


class TruthTests(unittest.TestCase):
    def test_night_is_recorded_before_the_day_vote(self) -> None:
        import tempfile
        from pathlib import Path

        directory = Path(tempfile.mkdtemp())
        truth_path = directory / "truth.json"
        seen = {}

        def on_step(env) -> None:
            if env.action_name == "vote_action" and "document" not in seen:
                seen["document"] = read_truth(truth_path)

        session = play(
            NIGHT_ROLES,
            0,
            _night_complete,
            truth_path=truth_path,
            on_step=on_step,
        )
        try:
            phases = [phase["phase"] for phase in seen["document"]["phases"]]
            self.assertIn("night-1", phases)
            self.assertNotIn("day-1", phases)
        finally:
            session.close()

    def test_exile_vote_on_the_update_has_a_modularity_gap(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        directory = Path(tempfile.mkdtemp())
        session = play(
            NIGHT_ROLES,
            0,
            _night_complete,
            truth_path=directory / "truth.json",
        )
        try:
            write_run_artifacts(session, NIGHT_ROLES, directory)
            gap = json.loads((directory / "gap.json").read_text(encoding="utf-8"))
            self.assertEqual(gap["modularity"], 0.0)
        finally:
            session.close()


class BadgeTests(unittest.TestCase):
    def test_exiled_sheriff_can_pass_the_badge(self) -> None:
        env = WerewolfEnv(
            {"Lacy": "wolf", "John": "wolf", "Mary": "villager", "Ethel": "villager"},
            max_days=2,
        )
        env.reset()
        env._sheriff = "Mary"
        env._phase = "vote_action"
        env.step(
            {
                "Lacy": {"action_vote": "Mary"},
                "John": {"action_vote": "Mary"},
                "Mary": {"action_vote": "Mary"},
                "Ethel": {"action_vote": "Mary"},
            }
        )
        self.assertEqual(env.asked, ["Mary"])
        self.assertEqual(env.action_name, "badge_flow")
        step = env.step(
            {
                "Mary": {
                    "action": {"pass_badge": True, "badge_receiver": "Ethel"},
                }
            }
        )
        contents = [line["content"] for line in step["observations"]["game_line"]]
        self.assertIn("Mary has passed the badge to Ethel.", contents)
        self.assertEqual(env._sheriff, "Ethel")
        self.assertEqual(env._phase, "werewolf_action")
        self.assertEqual(env._day, 2)

    def test_invalid_receiver_destroys_the_badge(self) -> None:
        env = WerewolfEnv(
            {"Lacy": "wolf", "Mary": "villager", "Ethel": "villager"},
            max_days=2,
        )
        env.reset()
        env._day = 2
        env._sheriff = "Mary"
        env._dead = ["Mary"]
        env._phase = "resolve"
        env.step({})
        self.assertEqual(env.asked, ["Mary"])
        step = env.step(
            {"Mary": {"action": {"pass_badge": False, "badge_receiver": "None"}}}
        )
        contents = [line["content"] for line in step["observations"]["game_line"]]
        self.assertIn("Mary has destroyed the badge.", contents)
        self.assertIsNone(env._sheriff)
        self.assertEqual(env.action_name, "player_speech")


class PromptTests(unittest.TestCase):
    def test_published_wolf_prompt_fills_history(self) -> None:
        prompt = load_prompt("werewolf_action")
        filled = fill_prompt(prompt["user"], "night opens", "", "")
        self.assertIn("night opens", filled)
        self.assertNotIn("<<public_chat>>", filled)
        self.assertTrue(prompt["tools"])


class VisibilityTests(unittest.TestCase):
    def test_wolf_line_is_absent_from_the_villager_view(self) -> None:
        session = play(ROLES, 2, _complete)
        try:
            outcomes = session.inspect("outcome")
            self.assertIn("target Ethel", lines_for(outcomes, "Lacy"))
            self.assertIn("target Ethel", lines_for(outcomes, "John"))
            self.assertNotIn("target Ethel", lines_for(outcomes, "Ethel"))
            outcome_text = " ".join(str(outcome.payload) for outcome in outcomes)
            self.assertNotIn("because Ethel", outcome_text)
            updates = session.inspect("agent_update")
            explanations = [
                update.payload.get("decision", {}).get("explanation")
                for update in updates
            ]
            self.assertIn("because Ethel", explanations)
        finally:
            session.close()

    def test_level_0_drops_the_explanation(self) -> None:
        session = play(ROLES, 0, _complete)
        try:
            updates = session.inspect("agent_update")
            for update in updates:
                decision = update.payload.get("decision", {})
                self.assertNotIn("explanation", decision)
        finally:
            session.close()


NIGHT_ROLES = {
    "Lacy": "wolf",
    "John": "wolf",
    "Mary": "guard",
    "David": "seer",
    "Sandra": "witch",
    "Ethel": "villager",
}


def _night_complete(messages, tools):
    del messages
    name = tools[0]["function"]["name"]
    if name in ("werewolf_action", "werewolf_consensus_action"):
        return {"action": {"attack": True, "target": "Ethel"}, "explanation": "pack"}
    if name == "guard_action":
        return {"action": {"protect_target": "Ethel"}, "explanation": "guard"}
    if name == "seer_action":
        return {"action": {"check_target": "Lacy"}, "explanation": "seer"}
    if name == "witch_action":
        return {
            "action": {"use_antidote": False, "use_poison": False},
            "explanation": "witch",
        }
    return {
        "action": {"run_for_sheriff": False, "action_vote": "abstain", "speech": "day"},
        "explanation": "day",
    }


class NightTests(unittest.TestCase):
    def test_private_night_lines_stay_with_their_roles(self) -> None:
        session = play(NIGHT_ROLES, 2, _night_complete)
        try:
            outcomes = session.inspect("outcome")
            self.assertIn("target Ethel", lines_for(outcomes, "Lacy"))
            self.assertNotIn("target Ethel", lines_for(outcomes, "Ethel"))
            self.assertIn("Guard protects Ethel.", lines_for(outcomes, "Mary"))
            self.assertNotIn("Guard protects Ethel.", lines_for(outcomes, "Ethel"))
            self.assertIn("The result is werewolf.", lines_for(outcomes, "David"))
            self.assertNotIn("The result is werewolf.", lines_for(outcomes, "Ethel"))
            self.assertIn("Night deaths: nobody.", lines_for(outcomes, "Ethel"))
            self.assertIn("Daily tasks:", lines_for(outcomes, "Ethel"))
            self.assertIn("exile_werewolf", lines_for(outcomes, "Ethel"))
            self.assertIn("Exile: nobody.", lines_for(outcomes, "Ethel"))
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
