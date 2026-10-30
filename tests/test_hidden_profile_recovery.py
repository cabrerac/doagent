"""Check remaining uncertainty for one question at one step."""

from __future__ import annotations

import unittest

from experiments.information_flow.hidden_profile.recovery import remaining_bits
from experiments.information_flow.queries import Answer


class HiddenProfileRecoveryTests(unittest.TestCase):
    """The curve stays at the prior until the view matches the rules."""

    def test_a_match_drops_to_zero_and_a_gap_stays_open(self) -> None:
        """Drop only when the view states the rules answer."""
        exact = Answer("exact", "agent-c")
        unknown = Answer("unknown")
        self.assertEqual(remaining_bits(unknown, unknown, 1.5), 1.5)
        self.assertEqual(remaining_bits(exact, exact, 1.5), 0.0)
        self.assertEqual(remaining_bits(exact, unknown, 1.5), 1.5)
        self.assertEqual(remaining_bits(exact, Answer("exact", "agent-a"), 1.5), 1.5)
