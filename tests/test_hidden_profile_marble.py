"""Test Hidden Profile played through MARBLE."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiments.information_flow.hidden_profile.access import COMPONENT_LOGS
from experiments.information_flow.hidden_profile.rules import run_episode
from experiments.information_flow.hidden_profile.run_marble import (
    log_body,
    run_marble,
    trace_body,
)
from experiments.information_flow.hidden_profile.service_trace import TRACE_NAME


class HiddenProfileMarbleTests(unittest.TestCase):
    """Check that MARBLE plays the same episode as the rules alone."""

    def test_engine_events_match_the_rules(self) -> None:
        """Replay one seed through the engine and through the rules."""
        with tempfile.TemporaryDirectory() as folder:
            rules = run_marble(17, folder)
            log_dir = Path(folder) / "logs"
            names = [
                "HiddenProfileEngine.log",
                "HiddenProfileEnv.log",
                "HiddenProfileAgent.agent-a.log",
                "HiddenProfileAgent.agent-b.log",
                "HiddenProfileAgent.agent-c.log",
            ]
            for name in names:
                path = log_dir / name
                self.assertTrue(path.is_file(), name)
                self.assertGreater(path.stat().st_size, 0, name)
            self.assertFalse((Path(folder) / "scoring_sink.json").exists())
        self.assertEqual(rules.episode(), run_episode(17))

    def test_each_view_writes_only_its_own_files(self) -> None:
        """Write one log, a subset, every log, or only the structured file."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            run_marble(17, root / "s1", condition="S1", names="HiddenProfileEnv.log")
            run_marble(
                17,
                root / "sk",
                condition="Sk",
                names=("HiddenProfileEnv.log", "HiddenProfileAgent.agent-a.log"),
            )
            run_marble(17, root / "sall", condition="Sall")
            run_marble(17, root / "trace", condition="Sstructured")
            self.assertEqual(_files(root / "s1"), {"HiddenProfileEnv.log"})
            self.assertEqual(
                _files(root / "sk"),
                {"HiddenProfileEnv.log", "HiddenProfileAgent.agent-a.log"},
            )
            self.assertEqual(_files(root / "sall"), set(COMPONENT_LOGS))
            self.assertEqual(_files(root / "trace"), {TRACE_NAME})

    def test_a_repeated_run_matches_once_the_clock_is_removed(self) -> None:
        """Replay one view and compare the lines without the clock."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            run_marble(17, root / "first", condition="Sall")
            run_marble(17, root / "second", condition="Sall")
            for name in COMPONENT_LOGS:
                self.assertEqual(
                    log_body(root / "first" / "logs" / name),
                    log_body(root / "second" / "logs" / name),
                )
            run_marble(17, root / "trace-a", condition="Sstructured")
            run_marble(17, root / "trace-b", condition="Sstructured")
            self.assertEqual(
                trace_body(root / "trace-a" / "logs" / TRACE_NAME),
                trace_body(root / "trace-b" / "logs" / TRACE_NAME),
            )

    def test_a_view_rejects_a_bad_name_list(self) -> None:
        """Reject a view whose log names do not fit that view."""
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                run_marble(17, folder, condition="S1")
            with self.assertRaises(ValueError):
                run_marble(17, folder, names="HiddenProfileEnv.log")


def _files(folder: Path) -> set[str]:
    """Return the file names written under one run's log directory."""
    return {path.name for path in (folder / "logs").iterdir() if path.is_file()}


if __name__ == "__main__":
    unittest.main()
