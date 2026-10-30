"""Score the Hidden Profile comparison and keep the known gaps."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiments.information_flow.hidden_profile.score import (
    QuestionScore,
    ScoreReport,
    score_deals,
)


class HiddenProfileScoreTests(unittest.TestCase):
    """Check wins, ties, and blanks on the questions the files already answer."""

    def test_the_score_keeps_known_gaps(self) -> None:
        """Score all 18 deals and keep the known gaps.

        The transition question is a tie.
        Every view says it is not stated, and so do the rules.
        Level 0 has no trace.
        The group votes and the vote bases are blanks against the logs.
        Level 1 matches the rules on those questions.
        The logs do not.
        """
        with tempfile.TemporaryDirectory() as folder:
            report = score_deals(folder)
            self.assertFalse((Path(folder) / "scoring_sink.json").exists())
            self.assertEqual(report.plot_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(report.deals, 18)
        self.assertEqual(len(report.views), 7)
        self._check_gaps(report)

    def _check_gaps(self, report: ScoreReport) -> None:
        """Check the gaps the comparison already showed."""
        by_name = {view.name: view for view in report.views}
        self.assertGreater(by_name["D1"].matched, by_name["S1"].matched)
        self.assertGreater(by_name["D1"].matched, by_name["Sall"].matched)
        self.assertGreater(by_name["D1"].mean_bytes_read, by_name["Sall"].mean_bytes_read)
        self.assertGreater(by_name["Sall"].mean_bytes_stored, by_name["Sall"].mean_bytes_read)
        self.assertEqual(by_name["D2"].matched, by_name["D1"].matched)
        self.assertLess(by_name["D0"].matched, by_name["D1"].matched)
        for view in report.views:
            self.assertGreaterEqual(view.share, 0.0)
            self.assertLessEqual(view.share, 1.0)
        for marble in ("S1", "Sk", "Sall", "Sstructured"):
            transition = _question(report, "transition", "D1", marble)
            self.assertEqual(transition.ties, 18)
            self.assertEqual(transition.wins, 0)
            self.assertEqual(transition.losses, 0)
            self.assertEqual(transition.blanks, 0)
            group = _question(report, "group_votes", "D1", marble)
            self.assertEqual(group.wins, 18)
            self.assertEqual(group.ties, 0)
            missing = _question(report, "group_votes", "D0", marble)
            self.assertEqual(missing.blanks, 18)
            self.assertEqual(missing.wins, 0)
            for index in range(3):
                basis = _question(report, f"bases.{index}", "D1", marble)
                self.assertEqual(basis.wins, 18)
                blank = _question(report, f"bases.{index}", "D0", marble)
                self.assertEqual(blank.blanks, 18)


def _question(report: ScoreReport, name: str, session: str, marble: str) -> QuestionScore:
    """Return one question row."""
    found = [
        question
        for question in report.questions
        if question.name == name
        and question.session == session
        and question.marble == marble
    ]
    if len(found) != 1:
        raise AssertionError(f"missing question row {name} {session} {marble}")
    return found[0]


if __name__ == "__main__":
    unittest.main()
