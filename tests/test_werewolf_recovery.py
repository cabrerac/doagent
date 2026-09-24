"""Recovery gaps for a fixed Werewolf night and day."""

import tempfile
import unittest
from pathlib import Path

from experiments.multiagentbench.recover import compare, slice_log
from experiments.multiagentbench.truth import read_truth, write_truth

POPULATION = 9
WOLVES = ["Patricia", "Jami", "Priscilla"]
VILLAGERS = ["Nicole", "Stephanie", "John", "David", "Mary", "Sandra"]


def _truth() -> dict:
    votes = {name: "Patricia" for name in VILLAGERS}
    votes.update({name: "David" for name in WOLVES})
    return {
        "phases": [
            {
                "phase": "night-1",
                "population_size": POPULATION,
                "facts": [
                    {"name": "protected John", "holders": ["John"]},
                    {"name": "target Nicole", "holders": WOLVES},
                    {"name": "checked Patricia", "holders": ["Nicole"]},
                ],
            },
            {
                "phase": "day-1",
                "population_size": POPULATION,
                "facts": [],
                "votes": votes,
            },
        ]
    }


def _logs() -> dict:
    night = {name: "Werewolves have chosen their target." for name in VILLAGERS + WOLVES}
    night["John"] = "protected John"
    for wolf in WOLVES:
        night[wolf] = "target Nicole"
    night["Nicole"] = "checked Patricia"
    day = {name: f"{name} voted for Patricia" for name in VILLAGERS}
    for wolf in WOLVES:
        day[wolf] = f"{wolf} voted for David"
        for villager in VILLAGERS:
            day[villager] += f"\n{wolf} voted for David"
    return {"night-1": night, "day-1": day}


class LogSliceTests(unittest.TestCase):
    def test_day_slice_stops_before_the_next_night(self) -> None:
        text = (
            "SYSTEM: Night 1 begins.\n"
            "John voted for Priscilla\n"
            "SYSTEM: Day 1 begins.\n"
            "John voted for Patricia\n"
            "SYSTEM: Night 2 begins.\n"
            "John voted for Mary\n"
        )
        day = slice_log(text, "day-1")
        self.assertIn("John voted for Patricia", day)
        self.assertNotIn("John voted for Mary", day)
        self.assertNotIn("Night 1 begins", day)


class RecoveryGapTests(unittest.TestCase):
    def test_matching_logs_have_zero_gap(self) -> None:
        gaps = compare(_truth(), _logs())
        self.assertEqual(gaps["entropy_gap"], 0.0)
        self.assertEqual(gaps["modularity_gap"], 0.0)

    def test_missing_name_is_a_total_miss(self) -> None:
        logs = _logs()
        for wolf in WOLVES:
            logs["night-1"][wolf] = "Werewolves have chosen their target."
        gaps = compare(_truth(), logs)
        self.assertAlmostEqual(gaps["entropy_gap"], 1 / 3)

    def test_missing_vote_is_a_total_miss(self) -> None:
        logs = _logs()
        logs["day-1"]["Sandra"] = "I have not voted."
        gaps = compare(_truth(), logs)
        self.assertEqual(gaps["modularity_gap"], 1.0)

    def test_truth_file_round_trip(self) -> None:
        document = _truth()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "truth.json"
            write_truth(path, document)
            self.assertEqual(read_truth(path), document)


if __name__ == "__main__":
    unittest.main()
