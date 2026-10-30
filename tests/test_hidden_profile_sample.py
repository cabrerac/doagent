"""Test sample counts against the exact Hidden Profile answers."""

from __future__ import annotations

import unittest

from experiments.information_flow.hidden_profile.sample import (
    PASS_LINE_BITS,
    RULE_KEEP,
    RULE_REPEATS,
    estimator_decision,
    repeated_deal_check,
    repeated_draw_check,
    sample_check,
)


class HiddenProfileSampleTests(unittest.TestCase):
    """Check a large sample against the exact values, and a small sample's error."""

    def test_large_sample_is_close_and_small_sample_reports_error(self) -> None:
        """Compare sample sizes 2, 18, and 4000 with the exact counts."""
        estimates = sample_check()
        large = [row for row in estimates if row.sample_size == 4000]
        small = [row for row in estimates if row.sample_size == 2]
        self.assertEqual(len(large), 82)
        self.assertEqual(len(small), 82)
        for row in large:
            self.assertLess(row.absolute_error, PASS_LINE_BITS, row.name)
        for row in small:
            self.assertGreaterEqual(row.absolute_error, 0.0)
        repeated = repeated_deal_check()
        holder = next(row for row in repeated if row.name == "bridge_holder_entropy")
        corrected = next(row for row in repeated if row.name == "bridge_holder_entropy_corrected")
        self.assertGreater(holder.exact, 0.5)
        self.assertAlmostEqual(holder.estimate, 0.0)
        self.assertAlmostEqual(holder.absolute_error, holder.exact)
        self.assertAlmostEqual(corrected.estimate, 0.0)
        self.assertGreater(corrected.absolute_error, PASS_LINE_BITS)
        brier = next(row for row in large if row.name == "belief_brier")
        self.assertEqual(brier.unit, "brier")

    def test_one_draw_uses_the_same_count_as_the_pass_line(self) -> None:
        """The repeated check accepts a draw only when it is inside the pass line."""
        single = sample_check(sample_sizes=(2,), seed=0)
        ruled = repeated_draw_check(sample_sizes=(2,), repeats=1, seed=0)
        self.assertEqual(len(ruled), 82)
        self.assertEqual(len(single), 82)
        for estimate in single:
            row = next(
                item
                for item in ruled
                if item.name == estimate.name
                and item.agent_id == estimate.agent_id
                and item.round_index == estimate.round_index
            )
            self.assertAlmostEqual(row.low, estimate.estimate)
            self.assertAlmostEqual(row.high, estimate.estimate)
            self.assertEqual(row.passes, int(estimate.absolute_error < PASS_LINE_BITS))

    def test_repeated_draws_keep_a_size_only_when_enough_repeats_pass(self) -> None:
        """Keep a sample size when 950 of 1,000 draws stay inside the pass line."""
        rows = repeated_draw_check()
        self.assertEqual(len(rows), 246)
        for row in rows:
            self.assertEqual(row.repeats, RULE_REPEATS)
            self.assertEqual(row.kept, row.passes / row.repeats >= RULE_KEEP)
            self.assertLessEqual(row.low, row.high)
        found = {
            (row.name, row.agent_id, row.round_index, row.sample_size): (row.passes, row.kept)
            for row in rows
        }
        self.assertEqual(found, _expected_draws())
        decision = estimator_decision(rows)
        self.assertEqual(decision.primary, "plug-in with a correction")
        self.assertEqual(decision.sample_size, 4000)
        self.assertEqual(decision.dropped, ())
        self.assertEqual(
            decision.corrected,
            (
                "bridge_delivery_mutual_information",
                "bridge_hold_multi_information",
                "bridge_holder_entropy",
                "held_signature_conditional_information",
            ),
        )
        self.assertTrue(decision.passed)
        holder = next(
            row
            for row in rows
            if row.name == "bridge_holder_entropy" and row.sample_size == 4000
        )
        corrected = next(
            row
            for row in rows
            if row.name == "bridge_holder_entropy_corrected" and row.sample_size == 4000
        )
        self.assertAlmostEqual(holder.coverage, 0.87, places=2)
        self.assertAlmostEqual(corrected.coverage, 0.95, places=2)
        self.assertLess(holder.mean_error, 0.0)
        self.assertGreater(corrected.coverage, holder.coverage)

    def test_repeated_draw_check_rejects_bad_arguments(self) -> None:
        """Reject a sample size, repeat count, pass line, or keep rate that cannot be used."""
        with self.assertRaises(ValueError):
            repeated_draw_check(sample_sizes=(0,))
        with self.assertRaises(ValueError):
            repeated_draw_check(repeats=0)
        with self.assertRaises(ValueError):
            repeated_draw_check(pass_line=0)
        with self.assertRaises(ValueError):
            repeated_draw_check(keep_rate=0)


def _expected_draws() -> dict[tuple[str, str | None, int | None, int], tuple[int, bool]]:
    """Return the locked pass count for every count and sample size."""
    agents = ("agent-a", "agent-b", "agent-c")
    rounds = (0, 1, 2)
    expected: dict[tuple[str, str | None, int | None, int], tuple[int, bool]] = {}
    expected[("bridge_holder_entropy", None, None, 2)] = (0, False)
    expected[("bridge_holder_entropy", None, None, 18)] = (419, False)
    expected[("bridge_holder_entropy", None, None, 4000)] = (1000, True)
    expected[("bridge_delivery_mutual_information", None, None, 2)] = (0, False)
    expected[("bridge_delivery_mutual_information", None, None, 18)] = (419, False)
    expected[("bridge_delivery_mutual_information", None, None, 4000)] = (1000, True)
    expected[("correct_option_entropy", None, None, 2)] = (1000, True)
    expected[("correct_option_entropy", None, None, 18)] = (1000, True)
    expected[("correct_option_entropy", None, None, 4000)] = (1000, True)
    belief_at_two = {
        ("agent-a", 0): 900,
        ("agent-b", 0): 903,
        ("agent-c", 0): 872,
        ("agent-a", 1): 903,
        ("agent-b", 1): 872,
        ("agent-c", 1): 900,
        ("agent-a", 2): 903,
        ("agent-b", 2): 872,
        ("agent-c", 2): 900,
    }
    for agent_id in agents:
        for round_index in rounds:
            expected[("belief_entropy", agent_id, round_index, 2)] = (
                belief_at_two[(agent_id, round_index)],
                False,
            )
            expected[("belief_entropy", agent_id, round_index, 18)] = (1000, True)
            expected[("belief_entropy", agent_id, round_index, 4000)] = (1000, True)
            for size in (2, 18, 4000):
                expected[("correct_option_entropy_given_held", agent_id, round_index, size)] = (
                    1000,
                    True,
                )
                expected[(
                    "correct_option_mutual_information",
                    agent_id,
                    round_index,
                    size,
                )] = (1000, True)
    for round_index in rounds:
        expected[("bridge_hold_multi_information", None, round_index, 2)] = (0, False)
        expected[("bridge_hold_multi_information", None, round_index, 18)] = (754, False)
        expected[("bridge_hold_multi_information", None, round_index, 4000)] = (1000, True)
        expected[("bridge_hold_multi_information_corrected", None, round_index, 2)] = (0, False)
        expected[("bridge_hold_multi_information_corrected", None, round_index, 18)] = (
            884,
            False,
        )
        expected[("bridge_hold_multi_information_corrected", None, round_index, 4000)] = (
            1000,
            True,
        )
        for size, passes, kept in ((2, 0, False), (18, 0, False), (4000, 1000, True)):
            expected[(
                "held_signature_conditional_information",
                None,
                round_index,
                size,
            )] = (passes, kept)
        expected[(
            "held_signature_conditional_information_corrected",
            None,
            round_index,
            2,
        )] = (0, False)
        expected[(
            "held_signature_conditional_information_corrected",
            None,
            round_index,
            18,
        )] = (59, False)
        expected[(
            "held_signature_conditional_information_corrected",
            None,
            round_index,
            4000,
        )] = (1000, True)
    given_at_18 = {("agent-a", 0): 45, ("agent-b", 0): 63, ("agent-c", 0): 62}
    for agent_id in agents:
        for round_index in rounds:
            for name in ("belief_brier", "belief_log_loss", "belief_relative_entropy"):
                for size in (2, 18, 4000):
                    expected[(name, agent_id, round_index, size)] = (1000, True)
            if round_index == 0:
                expected[(
                    "bridge_holder_entropy_given_held",
                    agent_id,
                    round_index,
                    2,
                )] = (0, False)
                expected[(
                    "bridge_holder_entropy_given_held",
                    agent_id,
                    round_index,
                    18,
                )] = (given_at_18[(agent_id, round_index)], False)
            else:
                expected[(
                    "bridge_holder_entropy_given_held",
                    agent_id,
                    round_index,
                    2,
                )] = (1000, True)
                expected[(
                    "bridge_holder_entropy_given_held",
                    agent_id,
                    round_index,
                    18,
                )] = (1000, True)
            expected[(
                "bridge_holder_entropy_given_held",
                agent_id,
                round_index,
                4000,
            )] = (1000, True)
    for size in (2, 18, 4000):
        expected[("decision_mutual_information", None, None, size)] = (1000, True)
        expected[("correct_option_entropy_corrected", None, None, size)] = (1000, True)
    expected[("bridge_holder_entropy_corrected", None, None, 2)] = (0, False)
    expected[("bridge_holder_entropy_corrected", None, None, 18)] = (550, False)
    expected[("bridge_holder_entropy_corrected", None, None, 4000)] = (1000, True)
    expected[("bridge_delivery_mutual_information_corrected", None, None, 2)] = (0, False)
    expected[("bridge_delivery_mutual_information_corrected", None, None, 18)] = (550, False)
    expected[("bridge_delivery_mutual_information_corrected", None, None, 4000)] = (
        1000,
        True,
    )
    return expected


if __name__ == "__main__":
    unittest.main()
