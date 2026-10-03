"""Rules shared with the published Werewolf night and day."""

from __future__ import annotations

import unittest

from experiments.multiagentbench.werewolf_doagent import WerewolfEnv, _majority


def _wolf_guard_village() -> WerewolfEnv:
    """Return a night with one wolf, a guard, and one villager."""
    env = WerewolfEnv(
        {"Lacy": "wolf", "Mary": "guard", "Ethel": "villager"},
        max_days=2,
    )
    env.reset()
    return env


class NightRuleTests(unittest.TestCase):
    def test_a_kill_lands_when_the_witch_is_already_gone(self) -> None:
        env = _wolf_guard_village()
        env.step({"Mary": {"protect_target": "Mary"}})
        step = env.step({"Lacy": {"attack": True, "target": "Ethel"}})
        contents = [line["content"] for line in step["observations"]["game_line"]]
        self.assertEqual(env.phases[-1]["deaths"], ["Ethel"])
        self.assertIn("Ethel", env._alive)
        self.assertNotIn("Ethel", env.asked)
        self.assertFalse(any(line.startswith("Night deaths:") for line in contents))
        step = env.step(
            {
                "Lacy": {"run_for_sheriff": False},
                "Mary": {"run_for_sheriff": False},
            }
        )
        contents = [line["content"] for line in step["observations"]["game_line"]]
        self.assertIn("Night deaths: Ethel", contents)
        self.assertEqual(env.asked, ["Ethel"])
        self.assertEqual(env.action_name, "last_words")

    def test_the_guard_saves_the_wolf_target(self) -> None:
        env = _wolf_guard_village()
        env.step({"Mary": {"protect_target": "Ethel"}})
        env.step({"Lacy": {"attack": True, "target": "Ethel"}})
        self.assertEqual(env.phases[-1]["deaths"], [])
        self.assertIn("Ethel", env._alive)

    def test_the_guard_cannot_protect_the_same_player_twice(self) -> None:
        env = _wolf_guard_village()
        env.step({"Mary": {"protect_target": "Mary"}})
        env.step({"Lacy": {"attack": False, "target": "Ethel"}})
        env._phase = "vote_action"
        env.step(
            {
                "Lacy": {"action_vote": "abstain"},
                "Mary": {"action_vote": "abstain"},
                "Ethel": {"action_vote": "abstain"},
            }
        )
        env.step({"Mary": {"protect_target": "Mary"}})
        env.step({"Lacy": {"attack": True, "target": "Ethel"}})
        self.assertIn("Ethel", env.phases[-1]["deaths"])

    def test_one_living_wolf_is_enough_to_choose_a_target(self) -> None:
        env = _wolf_guard_village()
        env.step({"Mary": {"protect_target": "Mary"}})
        env.step({"Lacy": {"attack": True, "target": "Ethel"}})
        self.assertEqual(env.phases[-1]["wolf_target"], "Ethel")


class DayRuleTests(unittest.TestCase):
    def test_the_unique_highest_vote_exiles_without_a_full_majority(self) -> None:
        env = WerewolfEnv(
            {
                "Lacy": "wolf",
                "Mary": "villager",
                "Ethel": "villager",
                "John": "villager",
            },
            max_days=1,
        )
        env.reset()
        env._phase = "vote_action"
        env.step(
            {
                "Lacy": {"action_vote": "Ethel"},
                "Mary": {"action_vote": "abstain"},
                "Ethel": {"action_vote": "abstain"},
                "John": {"action_vote": "abstain"},
            }
        )
        self.assertNotIn("Ethel", env._alive)
        self.assertEqual(env.phases[-1]["exile"], "Ethel")

    def test_a_tie_exiles_nobody(self) -> None:
        env = WerewolfEnv(
            {"Lacy": "wolf", "Mary": "villager", "Ethel": "villager"},
            max_days=1,
        )
        env.reset()
        env._phase = "vote_action"
        env.step(
            {
                "Lacy": {"action_vote": "Mary"},
                "Mary": {"action_vote": "Ethel"},
                "Ethel": {"action_vote": "abstain"},
            }
        )
        self.assertIsNone(env.phases[-1]["exile"])
        self.assertIn("Mary", env._alive)

    def test_the_sheriff_vote_weighs_more(self) -> None:
        winner = _majority(
            {"Mary": "Ethel", "Lacy": "John", "John": "abstain"},
            "Mary",
        )
        self.assertEqual(winner, "Ethel")

    def test_the_game_ends_when_only_a_wolf_remains(self) -> None:
        env = WerewolfEnv({"Lacy": "wolf", "Ethel": "villager"}, max_days=2)
        env.reset()
        env.step({"Lacy": {"attack": True, "target": "Ethel"}})
        self.assertNotIn("Ethel", env._alive)
        self.assertTrue(env.finished)
