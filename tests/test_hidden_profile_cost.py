"""Test wall-clock records for one Hidden Profile seed."""

from __future__ import annotations

import json
import statistics
import tempfile
import unittest
from pathlib import Path

from experiments.information_flow.hidden_profile.cost import record_wall_clock


class HiddenProfileCostTests(unittest.TestCase):
    """Check the cost file for DOAgent and for MARBLE."""

    def test_each_implementation_records_five_times(self) -> None:
        """Record five positive times, their median, and zero model calls."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for implementation in ("doagent", "marble"):
                record_wall_clock(implementation, 17, root / implementation)
            doagent = json.loads((root / "doagent" / "cost.json").read_text(encoding="utf-8"))
            marble = json.loads((root / "marble" / "cost.json").read_text(encoding="utf-8"))
        for name, payload in (("doagent", doagent), ("marble", marble)):
            self.assertEqual(payload["implementation"], name)
            self.assertEqual(payload["seed"], 17)
            self.assertEqual(payload["repeats"], 5)
            self.assertEqual(len(payload["wall_seconds"]), 5)
            self.assertTrue(all(sample > 0 for sample in payload["wall_seconds"]))
            self.assertEqual(payload["median_seconds"], statistics.median(payload["wall_seconds"]))
            self.assertEqual(payload["tokens"], 0)
            self.assertEqual(payload["model_calls"], 0)
        self.assertEqual(doagent["logging"], "level 1")
        self.assertEqual(marble["logging"], "all component logs")


if __name__ == "__main__":
    unittest.main()
