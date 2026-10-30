"""Test Hidden Profile played through a DOAgent session."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.information_flow.hidden_profile.cost import median, repeated_cost
from experiments.information_flow.hidden_profile.rules import run_episode
from experiments.information_flow.hidden_profile.run_doagent import (
    comparable_session,
    run_session,
)


class HiddenProfileDoagentTests(unittest.TestCase):
    """Check that a session plays the same episode as the rules alone."""

    def test_session_events_match_the_rules(self) -> None:
        """Replay one seed through the session and through the rules."""
        with tempfile.TemporaryDirectory() as folder:
            result = run_session(17, logging_level=1, output_base=folder)
        self.assertEqual(result.rules.episode(), run_episode(17))

    def test_each_logging_level_keeps_the_events(self) -> None:
        """Run levels 0, 1, and 2 without changing the episode."""
        direct = run_episode(4)
        for level in (0, 1, 2):
            with tempfile.TemporaryDirectory() as folder:
                result = run_session(4, logging_level=level, output_base=folder)
            self.assertEqual(result.rules.episode(), direct)

    def test_records_hold_outcomes_decisions_and_traces(self) -> None:
        """Export the session record kinds for one episode."""
        with tempfile.TemporaryDirectory() as folder:
            result = run_session(3, logging_level=1, output_base=folder)
            records = json.loads(result.records_path.read_text(encoding="utf-8"))
            self.assertTrue(result.records_path.is_file())
            self.assertFalse((Path(folder) / "scoring_sink.json").exists())
        self.assertEqual(set(records), {"agent_update", "outcome", "trace"})
        self.assertGreater(len(records["outcome"]), 0)
        self.assertGreater(len(records["agent_update"]), 0)
        self.assertGreater(len(records["trace"]), 0)
        self.assertNotIn("env_update", records)

    def test_a_repeated_session_matches_without_the_library_id_or_clock(self) -> None:
        """Replay each logging level and compare the records aside from id and clock."""
        for level in (0, 1, 2):
            with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
                left = run_session(17, logging_level=level, output_base=first)
                right = run_session(17, logging_level=level, output_base=second)
                left_bytes = left.records_path.read_bytes()
                right_bytes = right.records_path.read_bytes()
                left_text = json.loads(left_bytes)
                right_text = json.loads(right_bytes)
            self.assertEqual(comparable_session(left_text), comparable_session(right_text))
            if level == 1:
                self.assertNotEqual(left_bytes, right_bytes)

    def test_a_scripted_run_reports_no_tokens(self) -> None:
        """Count tokens as zero and accept a non-negative time."""
        self.assertEqual(median((1.0, 3.0, 2.0)), 2.0)

        def play() -> None:
            with tempfile.TemporaryDirectory() as folder:
                run_session(1, logging_level=0, output_base=folder)

        cost = repeated_cost("D0", play, repeats=1)
        self.assertEqual(cost.tokens, 0)
        self.assertGreaterEqual(cost.seconds, 0.0)


if __name__ == "__main__":
    unittest.main()
