"""Test the exact Hidden Profile deal count."""

from __future__ import annotations

import ast
import math
import unittest
from pathlib import Path

from experiments.information_flow.metrics import shannon_entropy
from experiments.information_flow.hidden_profile.reference import reference_report
from experiments.information_flow.hidden_profile.rules import run_episode

REFERENCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "experiments"
    / "information_flow"
    / "hidden_profile"
    / "reference.py"
)


class HiddenProfileReferenceTests(unittest.TestCase):
    """Check the eighteen deals and the quantities counted from them."""

    @classmethod
    def setUpClass(cls) -> None:
        """Count the reference deals once."""
        cls.report = reference_report()

    def test_module_imports_neither_framework(self) -> None:
        """Reject a framework import in the reference count."""
        tree = ast.parse(REFERENCE_PATH.read_text(encoding="utf-8"))
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
        self.assertFalse(any(name.startswith(("doagent", "marble")) for name in imported))

    def test_eighteen_deals_are_equally_likely(self) -> None:
        """Count 36 shuffles down to 18 deals."""
        report = self.report
        self.assertEqual(report.shuffle_count, 36)
        self.assertEqual(len(report.deals), 18)
        self.assertTrue(all(deal.count == 2 for deal in report.deals))
        self.assertTrue(
            all(math.isclose(deal.probability, 1 / 18) for deal in report.deals)
        )
        self.assertTrue(
            math.isclose(math.fsum(deal.probability for deal in report.deals), 1.0)
        )

    def test_correct_route_quantities_are_zero(self) -> None:
        """Check that the hill route does not vary across deals."""
        report = self.report
        self.assertTrue(all(deal.correct_option == "route-hill" for deal in report.deals))
        self.assertTrue(all(deal.group_decision == "route-hill" for deal in report.deals))
        self.assertTrue(math.isclose(report.correct_option_entropy, 0.0))
        self.assertTrue(
            all(math.isclose(item.value, 0.0) for item in report.correct_option_entropy_given_held)
        )
        self.assertTrue(
            all(
                math.isclose(item.value, 0.0)
                for item in report.correct_option_mutual_information
            )
        )

    def test_bridge_fact_has_log_three_bits(self) -> None:
        """Check the entropy and mutual information of the bridge fact."""
        report = self.report
        self.assertEqual(report.bridge_fact_id, "f6")
        self.assertTrue(math.isclose(report.bridge_holder_entropy, math.log2(3)))
        self.assertTrue(
            math.isclose(report.bridge_delivery_mutual_information, math.log2(3))
        )
        expected = 3 * shannon_entropy((1 / 3, 2 / 3)) - math.log2(3)
        self.assertEqual(len(report.bridge_hold_multi_information), 3)
        for _round_index, value in report.bridge_hold_multi_information:
            self.assertTrue(math.isclose(value, expected))

    def test_belief_entropy_is_shared_by_the_agents(self) -> None:
        """Check that each agent has the same average belief entropy."""
        grouped: dict[int, list[float]] = {}
        for item in self.report.belief_entropy:
            grouped.setdefault(item.round_index, []).append(item.value)
        self.assertEqual(set(grouped), {0, 1, 2})
        for values in grouped.values():
            self.assertEqual(len(values), 3)
            self.assertGreater(values[0], 0.0)
            self.assertTrue(all(math.isclose(value, values[0]) for value in values))

    def test_candidate_sets_match_the_deals(self) -> None:
        """Check the answers that still occur."""
        answers = {item.query: item for item in self.report.candidate_sets}
        holders = answers["who_was_dealt_the_bridge_fact"]
        self.assertEqual(holders.answers, ("agent-a", "agent-b", "agent-c"))
        self.assertTrue(math.isclose(holders.ambiguity, math.log2(3)))
        self.assertEqual(
            answers["who_received_the_bridge_fact"].answers,
            ("agent-a", "agent-b", "agent-c"),
        )
        self.assertEqual(answers["group_decision"].answers, ("route-hill",))
        self.assertEqual(answers["group_decision"].ambiguity, 0.0)
        self.assertEqual(
            answers["who_could_access_the_bridge_fact_after_round_0"].answers,
            holders.answers,
        )

    def test_seeded_episodes_use_the_counted_deals(self) -> None:
        """Match a seeded game to one counted deal."""
        known = {deal.allocation: deal for deal in self.report.deals}
        episode = run_episode(0)
        self.assertIn(episode.allocation, known)
        deal = known[episode.allocation]
        self.assertEqual(deal.held_fact_ids, episode.held_fact_ids)
        self.assertEqual(deal.group_decision, episode.group_decision)
        for seed in range(40):
            self.assertIn(run_episode(seed).allocation, known)


if __name__ == "__main__":
    unittest.main()
