"""Run one Hidden Profile study into a timestamped folder."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.information_flow.hidden_profile.study import run_study


class HiddenProfileStudyTests(unittest.TestCase):
    """Check that a second study leaves the first folder in place."""

    def test_a_second_run_keeps_the_first_folder(self) -> None:
        """Play one deal twice under two stamps.

        Each folder holds session levels 0, 1, and 2 and the MARBLE logs.
        The score and the figures are written beside those files.
        """
        with tempfile.TemporaryDirectory() as root:
            first = run_study(
                root,
                stamp="20261030_010000",
                deals=(0,),
                logging_levels=(0, 1, 2),
            )
            self.assertEqual(first.name, "hidden_profile_20261030_010000")
            self._check_folder(first)
            saved = (first / "deal-0" / "D1" / "records.json").read_bytes()
            second = run_study(
                root,
                stamp="20261030_010001",
                deals=(0,),
            )
            self.assertTrue((first / "deal-0" / "D1" / "records.json").read_bytes() == saved)
            self.assertNotEqual(first, second)
            self._check_folder(second)
            with self.assertRaises(FileExistsError):
                run_study(root, stamp="20261030_010000", deals=(0,))

    def _check_folder(self, folder: Path) -> None:
        """Check one study folder for the saved deal and the figures."""
        deal = folder / "deal-0"
        for name in ("D0", "D1", "D2"):
            self.assertTrue((deal / name / "records.json").is_file())
        self.assertTrue((deal / "marble" / "logs").is_dir())
        settings = json.loads((folder / "study.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["deals"], [0])
        self.assertEqual(settings["logging_levels"], [0, 1, 2])
        for name in (
            "score.json",
            "frontier.png",
            "questions.png",
            "dimensions.png",
            "curves.json",
            "belief_entropy.png",
            "bridge_quantities.png",
            "hold_multi_information.png",
            "breakdown.json",
            "recovery.png",
            "recovery.json",
            "campaign.json",
        ):
            path = folder / name
            self.assertTrue(path.is_file(), name)
        self.assertEqual((folder / "frontier.png").read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
