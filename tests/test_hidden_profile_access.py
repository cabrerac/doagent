"""Test analyst views over one MARBLE Hidden Profile run."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiments.information_flow.hidden_profile.access import COMPONENT_LOGS, analyst_logs
from experiments.information_flow.hidden_profile.run_marble import run_marble


class HiddenProfileAccessTests(unittest.TestCase):
    """Check which logs each analyst view may open."""

    def test_three_views_select_logs_from_one_run(self) -> None:
        """Open one log, the three agent logs, and every log."""
        with tempfile.TemporaryDirectory() as folder:
            run_marble(17, folder)
            log_dir = Path(folder) / "logs"
            one = analyst_logs(log_dir, "S1", "HiddenProfileAgent.agent-c.log")
            subset = analyst_logs(
                log_dir,
                "Sk",
                (
                    "HiddenProfileAgent.agent-a.log",
                    "HiddenProfileAgent.agent-b.log",
                    "HiddenProfileAgent.agent-c.log",
                ),
            )
            every = analyst_logs(log_dir, "Sall")
        self.assertEqual(one, (log_dir / "HiddenProfileAgent.agent-c.log",))
        self.assertEqual(
            subset,
            tuple(log_dir / name for name in COMPONENT_LOGS[2:]),
        )
        self.assertEqual(every, tuple(log_dir / name for name in COMPONENT_LOGS))


if __name__ == "__main__":
    unittest.main()
