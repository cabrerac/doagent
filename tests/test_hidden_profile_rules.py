"""Test Hidden Profile rules and the scripted policy."""

from __future__ import annotations

import ast
import math
import unittest
from pathlib import Path

from experiments.information_flow.events import BeliefEvent
from experiments.information_flow.hidden_profile.policies import scripted_policy
from experiments.information_flow.hidden_profile.rules import (
    DEFAULT_CONFIG,
    Fact,
    HiddenProfileConfig,
    HiddenProfileRules,
    run_episode,
    unique_leader,
)

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "experiments" / "information_flow" / "hidden_profile" / "rules.py"
POLICIES_PATH = ROOT / "experiments" / "information_flow" / "hidden_profile" / "policies.py"
SINK_KEYS = {
    "correct_option",
    "allocation",
    "held_fact_ids",
    "events",
    "group_decision",
}


class HiddenProfileRulesTests(unittest.TestCase):
    """Check the reference profile, privacy, and a scripted episode."""

    def test_modules_import_neither_framework(self) -> None:
        """Reject a framework import in the rules or the policy."""
        for path in (RULES_PATH, POLICIES_PATH):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported = [
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            ]
            imported.extend(
                node.module or ""
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            )
            self.assertFalse(
                any(name.startswith(("doagent", "marble")) for name in imported)
            )

    def test_reference_profile_is_hidden(self) -> None:
        """Check that only the complete fact set favours the hill route."""
        shared = tuple(fact for fact in DEFAULT_CONFIG.facts if fact.shared)
        self.assertEqual(
            unique_leader(shared, DEFAULT_CONFIG.options),
            "route-tunnel",
        )
        self.assertEqual(
            unique_leader(DEFAULT_CONFIG.facts, DEFAULT_CONFIG.options),
            "route-hill",
        )

    def test_configuration_rejects_a_visible_profile(self) -> None:
        """Reject facts whose shared scores already name the complete answer."""
        with self.assertRaises(ValueError):
            HiddenProfileConfig(
                options=("route-hill", "route-tunnel"),
                facts=(
                    Fact("f1", "route-hill", 2, True),
                    Fact("f2", "route-hill", 1, False),
                ),
                agents=("agent-a", "agent-b"),
            )

    def test_round_zero_hides_the_correct_option(self) -> None:
        """Check that no opening hand uniquely favours the hill route."""
        for seed in range(24):
            rules = HiddenProfileRules()
            observations = rules.reset(seed=seed)
            for observation in observations.values():
                origins = {fact["origin"] for fact in observation["held_facts"]}
                self.assertTrue(origins <= {"shared", "dealt"})
                held = _facts(observation["held_facts"])
                self.assertNotEqual(
                    unique_leader(held, DEFAULT_CONFIG.options),
                    "route-hill",
                )

    def test_identical_seeds_reproduce_the_sink(self) -> None:
        """Replay one seed into the same allocation, events, and decision."""
        self.assertEqual(run_episode(17), run_episode(17))

    def test_observations_hide_the_scoring_sink(self) -> None:
        """Keep other agents' facts and the sink out of each observation."""
        rules = HiddenProfileRules()
        observations = rules.reset(seed=17)
        policies = {
            agent_id: scripted_policy(agent_id)
            for agent_id in rules.agents
        }
        for _ in range(DEFAULT_CONFIG.horizon + 1):
            self._assert_private(observations)
            actions = {
                agent_id: policies[agent_id](
                    {"inputs": {"observation": observation}}
                )["choice"]["action"]
                for agent_id, observation in observations.items()
            }
            result = rules.step(actions)
            self.assertEqual(set(result), {"observations", "rewards", "done"})
            observations = result["observations"]
            if all(result["done"].values()):
                break
        self._assert_private(observations)
        episode = rules.episode()
        self.assertEqual(episode.correct_option, "route-hill")
        self.assertEqual(episode.group_decision, "route-hill")

    def test_a_received_fact_can_be_disclosed_onward(self) -> None:
        """Deliver a fact that the sender only received."""
        rules = HiddenProfileRules()
        observations = rules.reset(seed=3)
        result = rules.step(_scripted_actions(observations))
        observations = result["observations"]
        sender = next(
            agent_id
            for agent_id, observation in observations.items()
            if observation["received"]
        )
        fact_id = observations[sender]["received"][0]["fact_id"]
        recipient = observations[sender]["recipients"][0]
        actions = {
            agent_id: {"kind": "disclose", "fact_id": None, "recipients": ()}
            for agent_id in rules.agents
        }
        actions[sender] = {
            "kind": "disclose",
            "fact_id": fact_id,
            "recipients": (recipient,),
        }
        result = rules.step(actions)
        held_ids = [
            fact["fact_id"]
            for fact in result["observations"][recipient]["held_facts"]
        ]
        self.assertIn(fact_id, held_ids)

    def test_beliefs_sum_to_one(self) -> None:
        """Check every reported belief is a finite distribution."""
        episode = run_episode(5)
        beliefs = [
            event for event in episode.events if isinstance(event, BeliefEvent)
        ]
        self.assertGreaterEqual(len(beliefs), 3)
        for belief in beliefs:
            self.assertTrue(all(math.isfinite(value) for value in belief.probabilities))
            self.assertTrue(all(value >= 0.0 for value in belief.probabilities))
            self.assertTrue(math.isclose(math.fsum(belief.probabilities), 1.0))

    def test_event_order_is_strict(self) -> None:
        """Require a strictly increasing sequence index."""
        episode = run_episode(9)
        indexes = [event.sequence_index for event in episode.events]
        self.assertEqual(indexes, list(range(indexes[0], indexes[0] + len(indexes))))

    def test_scripted_episode_uses_no_framework(self) -> None:
        """Run one episode through the rules and the scripted policy."""
        episode = run_episode(11)
        self.assertEqual(episode.group_decision, "route-hill")
        self.assertTrue(episode.events)

    def _assert_private(self, observations: dict[str, dict[str, object]]) -> None:
        """Reject sink fields and facts the agent does not hold."""
        for observation in observations.values():
            self.assertTrue(SINK_KEYS.isdisjoint(observation))
            held_ids = {
                fact["fact_id"]
                for fact in observation["held_facts"]
            }
            received_ids = {fact["fact_id"] for fact in observation["received"]}
            self.assertTrue(received_ids <= held_ids)


def _scripted_actions(
    observations: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Return one scripted action per observation."""
    return {
        agent_id: scripted_policy(agent_id)(observation)["choice"]["action"]
        for agent_id, observation in observations.items()
    }


def _facts(held: object) -> tuple[Fact, ...]:
    """Rebuild facts from an observation view."""
    return tuple(
        Fact(
            str(fact["fact_id"]),
            str(fact["option"]),
            int(fact["weight"]),
            fact["origin"] == "shared",
        )
        for fact in held
    )


if __name__ == "__main__":
    unittest.main()
