"""Group Hidden Profile answers by dimension and by record or link."""

from __future__ import annotations

import unittest

from experiments.information_flow.hidden_profile.breakdown import (
    QuestionResult,
    _kind_share,
)


class HiddenProfileBreakdownTests(unittest.TestCase):
    """Keep questions the rules leave unstated out of the match rate."""

    def test_an_unstated_question_does_not_raise_the_share(self) -> None:
        """Ignore a question the rules do not state."""
        results = (
            QuestionResult("Traceability", "link", "Which update produced the group choice?", "D1", 0, 0, 18),
            QuestionResult("Traceability", "link", "What path did the bridge fact take?", "D1", 18, 18, 0),
        )
        self.assertEqual(_kind_share(results, "Traceability", "link", "D1"), 1.0)
        self.assertIsNone(_kind_share(results, "Explainability", "record", "D1"))


if __name__ == "__main__":
    unittest.main()
