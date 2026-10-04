"""Tests for the Werewolf outcome line and the level 2 explanation."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from experiments.multiagentbench.cost import (
    EXPLANATION_SUFFIX,
    explanation_overhead,
    overhead_from_records,
    projected_storage,
    service_log_paths,
    summarize_repetition,
    token_levels,
    write_cost,
)
from experiments.multiagentbench.run_werewolf_doagent import (
    assign_roles,
    call_model,
    generation_call,
    keep_going,
    log_model_request,
    play,
    prepare_game_dir,
    reply_action,
    unused_reply,
    write_run_artifacts,
)
from experiments.multiagentbench.truth import read_truth
from experiments.multiagentbench.werewolf_doagent import WerewolfEnv, _speech_order
from experiments.multiagentbench.werewolf_player import (
    fill_prompt,
    label_player_messages,
    load_prompt,
    task_suffix,
    werewolf_policy,
)
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
            record = directory / "outcome.jsonl"
            record.write_text("line\n", encoding="utf-8")
            write_cost(
                directory,
                1.5,
                None,
                [record, directory / "trace.jsonl"],
            )
            import json

            cost = json.loads((directory / "cost.json").read_text(encoding="utf-8"))
            self.assertEqual(cost["file_count"], 1)
            self.assertEqual(cost["storage_bytes"], record.stat().st_size)
            self.assertIsNone(cost["tokens"])
            self.assertEqual(cost["wall_seconds"], 1.5)
        finally:
            session.close()


class CostTests(unittest.TestCase):
    def test_level_0_drops_trace_and_explanation(self) -> None:
        records = [
            {
                "kind": "agent_update",
                "id": "a",
                "actor": "John",
                "timestamp": "t",
                "payload": {
                    "decision": {
                        "explanation": "because",
                        "request": {},
                        "response": {"reasoning": {"steps": [1]}},
                    }
                },
                "provenance": {"created_by": "John"},
                "accountability": {"owner": "John"},
            },
            {
                "kind": "trace",
                "id": "b",
                "actor": "John",
                "timestamp": "t",
                "payload": {"from_id": "x", "to_id": "y"},
                "provenance": {"created_by": "John"},
                "accountability": {"owner": "John"},
            },
        ]
        level_0 = projected_storage(records, 0)
        level_2 = projected_storage(records, 2)
        self.assertEqual(level_0["file_count"], 1)
        self.assertEqual(level_2["file_count"], 2)
        self.assertLess(level_0["storage_bytes"], level_2["storage_bytes"])

    def test_service_cost_counts_player_logs(self) -> None:
        import tempfile
        from pathlib import Path

        directory = Path(tempfile.mkdtemp())
        (directory / "checkpoint_Day1.json").write_text("{}", encoding="utf-8")
        log = directory / "1-wolf-John_log.txt"
        log.write_text("voted for Mary\n", encoding="utf-8")
        self.assertEqual(service_log_paths(directory), [log])
        write_cost(directory, 2.0, 10, service_log_paths(directory))
        import json

        cost = json.loads((directory / "cost.json").read_text(encoding="utf-8"))
        self.assertEqual(cost["file_count"], 1)
        self.assertEqual(cost["storage_bytes"], log.stat().st_size)

    def test_explanation_overhead_counts_request_and_reply(self) -> None:
        def encode(text: str) -> list[int]:
            return [1] * len(text)

        user = f"You are John.\n\nDecide.{EXPLANATION_SUFFIX}"
        overhead = explanation_overhead(user, "because", encode)
        self.assertEqual(overhead, len(EXPLANATION_SUFFIX) + len("because"))
        self.assertEqual(explanation_overhead("Decide.", "because", encode), len("because"))

    def test_level_tokens_drop_the_explanation(self) -> None:
        levels = token_levels(100, 10)
        self.assertEqual(levels, {"0": 90, "1": 90, "2": 100})
        self.assertEqual(token_levels(5, 9), {"0": 0, "1": 0, "2": 5})

    def test_summary_subtracts_explanations_from_a_level_2_session(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        def encode(text: str) -> list[int]:
            return [1] * len(text)

        record = {
            "kind": "agent_update",
            "payload": {
                "decision": {
                    "explanation": "hi",
                    "response": {"explanation": "hi"},
                }
            },
        }
        repetition = Path(tempfile.mkdtemp())
        records = repetition / "doagent" / "werewolf_doagent_run_x" / "records"
        records.mkdir(parents=True)
        (records / "agent_update.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
        (repetition / "doagent" / "cost.json").write_text(
            json.dumps({"tokens": 1000, "wall_seconds": 3.5}),
            encoding="utf-8",
        )
        summary = summarize_repetition(repetition, encode)
        overhead = overhead_from_records([record], encode)
        self.assertEqual(summary["doagent"]["2"]["tokens"], 1000)
        self.assertEqual(summary["doagent"]["0"]["tokens"], 1000 - overhead)
        self.assertEqual(summary["doagent"]["1"]["tokens"], 1000 - overhead)
        self.assertEqual(summary["doagent"]["0"]["wall_seconds"], 3.5)
        self.assertGreater(overhead, len("hi"))

    def test_summary_uses_the_stored_split(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        repetition = Path(tempfile.mkdtemp())
        records = repetition / "doagent" / "werewolf_doagent_run_x" / "records"
        records.mkdir(parents=True)
        record = {
            "kind": "agent_update",
            "payload": {"decision": {"explanation": "hi", "response": {"explanation": "hi"}}},
        }
        (records / "agent_update.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
        (repetition / "doagent" / "cost.json").write_text(
            json.dumps(
                {
                    "tokens": 50,
                    "wall_seconds": 1.0,
                    "tokens_by_level": {"0": 10, "1": 10, "2": 50},
                }
            ),
            encoding="utf-8",
        )

        def encode(text: str) -> list[int]:
            raise AssertionError(text)

        summary = summarize_repetition(repetition, encode)
        self.assertEqual(summary["doagent"]["0"]["tokens"], 10)
        self.assertEqual(summary["doagent"]["2"]["tokens"], 50)


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
            self.assertEqual(gap["entropy"], 0.0)
            curve = json.loads((directory / "curve.json").read_text(encoding="utf-8"))
            propositions = [
                fact["proposition"]
                for episode in curve["episodes"]
                for fact in episode["facts"]
            ]
            self.assertIn("target Ethel", propositions)
            self.assertIn("Guard protects Ethel.", propositions)
            self.assertNotIn("Werewolves have chosen their target.", propositions)
            for outcome in session.inspect("outcome"):
                self.assertNotIn("curve", outcome.payload.get("observations") or {})
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


def _printed_request(kind: str, detail: str) -> str:
    """Return the stdout from one logged model request."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        log_model_request(
            [{"role": "user", "content": "Alive players: Ethel"}],
            [{"function": {"name": "werewolf_action"}}],
            kind,
            detail,
        )
    return buffer.getvalue()


class PromptTests(unittest.TestCase):
    def test_published_wolf_prompt_fills_history(self) -> None:
        prompt = load_prompt("werewolf_action")
        filled = fill_prompt(
            prompt["user"],
            {"public_chat": "night opens", "game_state": "", "player info": ""},
        )
        self.assertIn("night opens", filled)
        self.assertNotIn("<<public_chat>>", filled)
        self.assertTrue(prompt["tools"])

    def test_wolf_observation_names_the_living_players(self) -> None:
        env = WerewolfEnv(NIGHT_ROLES)
        env.reset()
        env._phase = "werewolf_action"
        obs = env._open_ask()
        self.assertIn("Lacy", obs["Lacy"]["game_state"])
        self.assertIn("night", obs["Lacy"]["game_state"])
        self.assertIn("Alive werewolves: Lacy, John", obs["Lacy"]["player_info"])
        self.assertEqual(obs["Lacy"]["player_info"].count("Ethel"), 1)

    def test_policy_fills_game_state_from_the_observation(self) -> None:
        seen = {}

        def complete(messages, tools):
            del tools
            seen["user"] = messages[1]["content"]
            return {"action": {"attack": True, "target": "Ethel"}, "explanation": "pack"}

        policy = werewolf_policy("Lacy", lambda: "chat", 0, complete)({})
        policy(
            {
                "inputs": {
                    "observation": {
                        "action": "werewolf_action",
                        "game_state": '{"days": 1}',
                        "player_info": "Alive players: Ethel",
                    }
                }
            }
        )
        self.assertIn("chat", seen["user"])
        self.assertIn('{"days": 1}', seen["user"])
        self.assertIn("Alive players: Ethel", seen["user"])
        self.assertTrue(seen["user"].startswith("You are Lacy."))
        self.assertNotIn("<<game_state>>", seen["user"])
        self.assertNotIn("<<player info>>", seen["user"])

    def test_service_messages_name_the_acting_player(self) -> None:
        messages = label_player_messages(
            [
                {"role": "system", "content": "night"},
                {"role": "user", "content": "Alive players: Ethel"},
            ],
            "Nicole",
        )
        self.assertEqual(messages[0]["content"], "night")
        self.assertTrue(messages[1]["content"].startswith("You are Nicole."))
        self.assertIn("Alive players: Ethel", messages[1]["content"])

    def test_villager_prompt_gets_the_task_block(self) -> None:
        text = task_suffix(
            "villager",
            ["exile_werewolf", "protect_seer", "poison_werewolf"],
            True,
        )
        self.assertIn("exile_werewolf:", text)
        self.assertNotIn("poison_werewolf", text)
        self.assertIn("cooperative strategy", text)

    def test_wolf_prompt_skips_the_strategy_line(self) -> None:
        text = task_suffix("wolf", ["exile_werewolf", "poison_werewolf"], False)
        self.assertIn("exile_werewolf:", text)
        self.assertNotIn("poison_werewolf", text)
        self.assertNotIn("cooperative strategy", text)

    def test_witch_prompt_includes_the_potion_tasks(self) -> None:
        text = task_suffix(
            "witch",
            ["poison_werewolf", "rescue_villager", "exile_werewolf"],
            True,
        )
        self.assertIn("poison_werewolf:", text)
        self.assertIn("rescue_villager:", text)

    def test_model_call_uses_temperature_0_7(self) -> None:
        import inspect

        source = inspect.getsource(call_model)
        self.assertIn("temperature=0.7", source)
        self.assertIn("call_with_retry", source)
        self.assertIn("generation_call", source)
        self.assertIn("unused_reply", source)

    def test_sheriff_prompt_fills_the_election_fields(self) -> None:
        env = WerewolfEnv({"Lacy": "wolf", "Ethel": "villager", "Mary": "villager"})
        env.reset()
        env._phase = "sheriff_speech"
        env._candidates = ["Lacy", "Ethel"]
        env._candidate_index = 1
        env._election_speeches = [("Lacy", "I serve")]
        obs = env._observation("Ethel")
        prompt = load_prompt("sheriff_speech")
        fields = {
            "public_chat": "chat",
            "game_state": obs["game_state"],
            "player info": obs["player_info"],
        }
        fields.update(obs["fields"])
        filled = fill_prompt(prompt["user"], fields)
        self.assertNotIn("<<", filled)
        self.assertIn("I serve", filled)
        self.assertIn("Lacy, Ethel", filled)

    def test_rejected_request_prints_the_user_prompt(self) -> None:
        text = _printed_request("Rejected", "model reply returned in 0.1s")
        self.assertIn(
            "Rejected model request. Tool werewolf_action. model reply returned in 0.1s",
            text,
        )
        self.assertIn("Alive players: Ethel", text)

    def test_kept_request_prints_the_user_prompt(self) -> None:
        text = _printed_request("Kept", "12.0s")
        self.assertIn("Kept model request. Tool werewolf_action. 12.0s", text)
        self.assertIn("Alive players: Ethel", text)


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


class ReplyTests(unittest.TestCase):
    def test_generation_call_waits_five_seconds(self) -> None:
        waits = []
        tries = {"count": 0}

        def operation() -> str:
            tries["count"] += 1
            if tries["count"] < 3:
                raise TimeoutError("Request timed out.")
            return "ok"

        result = generation_call(operation, pause=waits.append)
        self.assertEqual(result, "ok")
        self.assertEqual(waits, [5, 5])

    def test_generation_call_stops_after_four_failures(self) -> None:
        waits = []

        def operation() -> str:
            raise TimeoutError("Request timed out.")

        with self.assertRaises(Exception) as caught:
            generation_call(operation, pause=waits.append)
        self.assertEqual(str(caught.exception), "Chat Completion failed too many times")
        self.assertEqual(waits, [5, 5, 5, 5])

    def test_missing_tool_call_is_unused(self) -> None:
        message = type("Message", (), {"tool_calls": None})()
        self.assertIsNone(reply_action(message))
        self.assertEqual(unused_reply(3)["action"], "no_action")
        self.assertEqual(unused_reply(3)["target"], None)
        self.assertEqual(unused_reply(3)["tokens"], 3)

    def test_arguments_that_are_not_json_are_unused(self) -> None:
        call = type(
            "Call",
            (),
            {"function": type("Fn", (), {"arguments": "not json"})()},
        )()
        message = type("Message", (), {"tool_calls": [call]})()
        self.assertIsNone(reply_action(message))

    def test_missing_speech_uses_the_service_sentence(self) -> None:
        env = WerewolfEnv({"Lacy": "wolf", "Ethel": "villager"})
        env.reset()
        env._phase = "player_speech"
        env._speech_order = ["Ethel"]
        env._speaker_index = 0
        step = env.step({"Ethel": "no_action"})
        contents = [line["content"] for line in step["observations"]["game_line"]]
        self.assertIn("Error during generation for player Ethel.", contents)

    def test_published_speech_field_is_kept(self) -> None:
        env = WerewolfEnv({"Lacy": "wolf", "Ethel": "villager"})
        env.reset()
        env._phase = "player_speech"
        env._speech_order = ["Ethel"]
        env._speaker_index = 0
        step = env.step({"Ethel": {"action": {"speech_content": "I am Ethel."}}})
        contents = [line["content"] for line in step["observations"]["game_line"]]
        self.assertIn("I am Ethel.", contents)

    def test_seer_does_not_invent_a_result(self) -> None:
        env = WerewolfEnv({"Lacy": "wolf", "David": "seer", "Ethel": "villager"})
        env.reset()
        env._phase = "seer"
        step = env.step({"David": "no_action"})
        contents = [line["content"] for line in step["observations"]["game_line"]]
        text = " ".join(contents)
        self.assertIn("Seer action failed.", text)
        self.assertIn("Seer has checked a player's identity.", text)
        self.assertNotIn("not a werewolf", text)
        self.assertEqual(env._seer_checks, [])


class SheriffSpeechTests(unittest.TestCase):
    def test_a_candidate_who_continues_stays_on_the_ballot(self) -> None:
        env = WerewolfEnv({"Lacy": "wolf", "Ethel": "villager", "Mary": "villager"})
        env.reset()
        env._phase = "sheriff_speech"
        env._candidates = ["Lacy", "Ethel"]
        env._candidate_index = 0
        step = env.step(
            {
                "Lacy": {
                    "action": {
                        "continue_running": True,
                        "speech_content": "I stay.",
                    }
                }
            }
        )
        contents = [line["content"] for line in step["observations"]["game_line"]]
        self.assertIn("I stay.", contents)
        self.assertNotIn("Lacy has withdrawn from the sheriff election.", contents)
        self.assertEqual(env._final_candidates, ["Lacy"])
        self.assertEqual(env.action_name, "sheriff_speech")

    def test_a_candidate_who_does_not_continue_withdraws(self) -> None:
        env = WerewolfEnv({"Lacy": "wolf", "Ethel": "villager", "Mary": "villager"})
        env.reset()
        env._phase = "sheriff_speech"
        env._candidates = ["Lacy", "Ethel"]
        env._final_candidates = ["Lacy"]
        env._candidate_index = 1
        step = env.step({"Ethel": {"action": {"speech_content": "I step down."}}})
        contents = [line["content"] for line in step["observations"]["game_line"]]
        self.assertIn("Ethel has withdrawn from the sheriff election.", contents)
        self.assertEqual(env._final_candidates, ["Lacy"])
        self.assertEqual(env.action_name, "vote_for_sheriff")
        self.assertEqual(env.asked, ["Mary"])
        self.assertEqual(env._observation("Mary")["fields"]["candidate_list"], "Lacy")

    def test_an_unusable_sheriff_speech_withdraws(self) -> None:
        env = WerewolfEnv({"Lacy": "wolf", "Mary": "villager"})
        env.reset()
        env._phase = "sheriff_speech"
        env._candidates = ["Lacy"]
        env._candidate_index = 0
        step = env.step({"Lacy": "no_action"})
        contents = [line["content"] for line in step["observations"]["game_line"]]
        self.assertIn("Error during generation for player Lacy.", contents)
        self.assertIn("Lacy has withdrawn from the sheriff election.", contents)
        self.assertEqual(env._final_candidates, [])


class FolderTests(unittest.TestCase):
    def test_a_game_folder_is_created(self) -> None:
        import tempfile
        from pathlib import Path

        root = Path(tempfile.mkdtemp())
        folder = prepare_game_dir(str(root / "01" / "doagent"), root / "service")
        self.assertEqual(folder, (root / "01" / "doagent").resolve())
        self.assertTrue(folder.is_dir())


class ScoreTests(unittest.TestCase):
    def test_a_score_failure_is_logged(self) -> None:
        def boom() -> None:
            raise ValueError("modularity needs at least two choices")

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            keep_going("Gap scoring", boom)
        self.assertIn(
            "Gap scoring failed: modularity needs at least two choices",
            buffer.getvalue(),
        )


class NightTests(unittest.TestCase):
    def test_night_closes_after_the_witch_is_gone(self) -> None:
        env = WerewolfEnv(
            {"Lacy": "wolf", "Mary": "guard", "Ethel": "villager"},
            max_days=1,
        )
        env.reset()
        env.step({"Mary": {"protect_target": "Mary"}})
        step = env.step({"Lacy": {"attack": True, "target": "Ethel"}})
        contents = [line["content"] for line in step["observations"]["game_line"]]
        self.assertIn("Ethel", env._alive)
        self.assertNotIn("Ethel", env.asked)
        self.assertNotIn("Seer has checked a player's identity.", contents)
        self.assertNotIn("Witch has made her decision on potion use.", contents)
        self.assertEqual(env.phases[0]["phase"], "night-1")
        self.assertEqual(env.phases[0]["deaths"], ["Ethel"])
        self.assertEqual(env.phases[0]["wolf_target"], "Ethel")


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
            self.assertNotIn("Daily tasks:", lines_for(outcomes, "Ethel"))
            self.assertIn("Exile: nobody.", lines_for(outcomes, "Ethel"))
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
