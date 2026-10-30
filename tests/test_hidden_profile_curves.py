"""Recover Hidden Profile information curves from the session file and the logs."""

from __future__ import annotations

import tempfile
import unittest

from experiments.information_flow.hidden_profile.curves import (
    CurvePoint,
    CurveReport,
    recover_curves,
)


class HiddenProfileCurveTests(unittest.TestCase):
    """Check which files recover the true curves and which leave them unstated."""

    def test_session_recovers_the_curves_and_logs_leave_beliefs_unstated(self) -> None:
        """Recover all 18 deals and keep the known gaps.

        The session file matches the rules.
        The MARBLE files do not state reported chances.
        Agent C's log and the three agent logs do not state the opening hands.
        """
        with tempfile.TemporaryDirectory() as folder:
            report = recover_curves(folder)
            for path in (report.belief_plot, report.bridge_plot, report.multi_plot):
                self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(report.deals, 18)
        self._check(report)

    def _check(self, report: CurveReport) -> None:
        """Check recovery against the rules."""
        for point in report.points:
            if point.view == "rules":
                continue
            truth = _rules_value(report, point)
            if point.view in ("D0", "D1", "D2"):
                self.assertIsNotNone(point.bits)
                self.assertAlmostEqual(point.bits, truth, places=6)
            if point.quantity == "belief_entropy" and point.view.startswith("S"):
                self.assertIsNone(point.bits)
            if point.view in ("S1", "Sk") and point.quantity != "belief_entropy":
                self.assertIsNone(point.bits)
            if point.view in ("Sall", "Sstructured") and point.quantity != "belief_entropy":
                self.assertIsNotNone(point.bits)
                self.assertAlmostEqual(point.bits, truth, places=6)


def _rules_value(report: CurveReport, point: CurvePoint) -> float:
    """Return the rules value for the same quantity."""
    matches = [
        item.bits
        for item in report.points
        if item.view == "rules"
        and item.quantity == point.quantity
        and item.agent_id == point.agent_id
        and item.round_index == point.round_index
    ]
    if len(matches) != 1 or matches[0] is None:
        raise AssertionError("the rules must state one value")
    return matches[0]


if __name__ == "__main__":
    unittest.main()
