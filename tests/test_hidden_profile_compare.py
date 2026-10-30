"""Test the frozen questions on every Hidden Profile deal."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.information_flow.hidden_profile.compare import (
    AGENT_LOGS,
    ONE_LOG,
    DealComparison,
    compare_deals,
)
from experiments.information_flow.hidden_profile.reading import ReadingCost
from experiments.information_flow.hidden_profile.service_trace import (
    LINE_FIELDS,
    PARENT_ID,
    TRACE_NAME,
)
from experiments.information_flow.queries import Answer


class HiddenProfileCompareTests(unittest.TestCase):
    """Check full artifacts against the rules, and gaps where the deal line is missing."""

    def test_full_files_match_and_missing_deal_is_unknown(self) -> None:
        """Compare all 18 deals from the rules, DOAgent, and MARBLE."""
        with tempfile.TemporaryDirectory() as folder:
            comparisons = compare_deals(folder)
            self.assertTrue((Path(folder) / "comparison.json").is_file())
            self.assertFalse((Path(folder) / "scoring_sink.json").exists())
            self.assertEqual(len(comparisons), 18)
            for comparison in comparisons:
                self._check_deal(Path(folder), comparison)

    def _check_deal(self, folder: Path, comparison: DealComparison) -> None:
        """Check one deal's answers and the cost of reading each view."""
        views = {view.source: view for view in comparison.views}
        rules = views["rules"]
        self.assertIsNone(rules.reading)
        for source in ("doagent", "marble_sall", "marble_structured"):
            self.assertEqual(views[source].recipients, rules.recipients, comparison.index)
            self.assertEqual(views[source].access_before, rules.access_before, comparison.index)
            self.assertEqual(views[source].access_after, rules.access_after, comparison.index)
            self.assertEqual(views[source].votes, rules.votes, comparison.index)
            self.assertEqual(views[source].transition, Answer("unknown"))
        self.assertEqual(views["doagent"].group_votes, rules.group_votes, comparison.index)
        self.assertEqual(views["doagent"].belief_change, rules.belief_change, comparison.index)
        for source in ("marble_sall", "marble_structured"):
            self.assertEqual(views[source].group_votes, Answer("unknown"))
            self.assertEqual(views[source].belief_change, Answer("unknown"))
        for source in ("doagent", "marble_sall"):
            self.assertEqual(views[source].sender, rules.sender, comparison.index)
            self.assertEqual(views[source].bridge_path, rules.bridge_path, comparison.index)
        self.assertEqual(views["doagent"].chances, rules.chances, comparison.index)
        self.assertEqual(rules.group_votes.kind, "exact")
        self.assertEqual(rules.belief_change.kind, "exact")
        self.assertEqual(rules.transition, Answer("unknown"))
        self.assertTrue(all(answer.kind == "exact" for answer in rules.vote_match))
        self.assertEqual(views["doagent"].vote_match, rules.vote_match, comparison.index)
        self.assertEqual(views["doagent"].bases, rules.bases, comparison.index)
        self.assertTrue(all(answer.kind == "exact" for answer in rules.bases))
        unknown = tuple(Answer("unknown") for _ in rules.bases)
        for source in ("marble_sall", "marble_agents", "marble_one", "marble_structured"):
            self.assertEqual(views[source].bases, unknown, comparison.index)
            self.assertEqual(views[source].vote_match, unknown, comparison.index)
            self.assertEqual(views[source].chances, Answer("unknown"), comparison.index)
        agents = views["marble_agents"]
        self.assertEqual(agents.access_before, Answer("unknown"), comparison.index)
        self.assertEqual(agents.access_after, Answer("unknown"), comparison.index)
        self.assertEqual(agents.recipients, rules.recipients, comparison.index)
        deal = folder / f"deal-{comparison.index}"
        log_dir = deal / "marble" / "logs"
        records = deal / "doagent" / "records.json"
        agent_paths = [log_dir / name for name in AGENT_LOGS]
        one_path = log_dir / ONE_LOG
        env_path = log_dir / "HiddenProfileEnv.log"
        engine_path = log_dir / "HiddenProfileEngine.log"
        self._check_reading(views["doagent"].reading, 1, 0, records.stat().st_size)
        self._check_reading(views["marble_one"].reading, 1, 0, one_path.stat().st_size)
        self._check_reading(
            views["marble_agents"].reading,
            3,
            1,
            sum(path.stat().st_size for path in agent_paths),
        )
        read_bytes = env_path.stat().st_size + sum(path.stat().st_size for path in agent_paths)
        self._check_reading(views["marble_sall"].reading, 4, 2, read_bytes)
        trace_path = log_dir / TRACE_NAME
        self._check_reading(views["marble_structured"].reading, 1, 0, trace_path.stat().st_size)
        self._check_trace_schema(trace_path)
        self.assertGreater(engine_path.stat().st_size, 0)
        self.assertLess(
            views["marble_sall"].reading.bytes_read,
            read_bytes + engine_path.stat().st_size,
        )

    def _check_reading(
        self,
        reading: ReadingCost | None,
        files_opened: int,
        joins: int,
        bytes_read: int,
    ) -> None:
        """Check one view's file count, join count, and byte total."""
        self.assertIsNotNone(reading)
        assert reading is not None
        self.assertEqual(reading.files_opened, files_opened)
        self.assertEqual(reading.joins, joins)
        self.assertEqual(reading.bytes_read, bytes_read)

    def _check_trace_schema(self, path: Path) -> None:
        """Check that the trace uses the service fields and the engine parent."""
        lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        self.assertGreaterEqual(len(lines), 2)
        for line in lines:
            self.assertEqual(tuple(sorted(line)), LINE_FIELDS)
        self.assertIsNone(lines[0]["parent_id"])
        self.assertEqual(lines[1]["parent_id"], PARENT_ID)
        self.assertEqual(lines[1]["operation"], "deal")


if __name__ == "__main__":
    unittest.main()
