"""Truth phases copied from Werewolf state."""

import unittest

from experiments.multiagentbench.werewolf_truth import day_phase, night_phase


def _state() -> dict:
    return {
        "public_state": {
            "days": 1,
            "day_cache": [
                {
                    "banishment_votes": {
                        "Stephanie": "Patricia",
                        "Patricia": "David",
                    }
                }
            ],
        },
        "private_state": {
            "players": {
                "John": {"role": "guard", "status": {"health": 1, "check_history": {}}},
                "Nicole": {
                    "role": "seer",
                    "status": {
                        "health": 1,
                        "check_history": {
                            "Night 1": {"player": "Patricia", "result": "werewolf"}
                        },
                    },
                },
                "David": {"role": "witch", "status": {"health": 1}},
                "Patricia": {"role": "wolf", "status": {"health": 1}},
                "Jami": {"role": "wolf", "status": {"health": 1}},
            },
            "night_cache": [
                {
                    "guard_action": "John",
                    "werewolf_action": {"final_target": "Nicole"},
                    "witch_action": {"action": "none", "target": None},
                }
            ],
        },
    }


class WerewolfTruthTests(unittest.TestCase):
    def test_night_records_holders(self) -> None:
        phase = night_phase(_state())
        self.assertEqual(phase["phase"], "night-1")
        self.assertEqual(phase["population_size"], 5)
        by_name = {fact["name"]: fact["holders"] for fact in phase["facts"]}
        self.assertEqual(by_name["John is protected this night."], ["John"])
        self.assertEqual(by_name["Final Target: Nicole"], ["Patricia", "Jami"])
        self.assertEqual(by_name["You have checked Patricia"], ["Nicole"])
        self.assertNotIn("votes", phase)

    def test_day_records_votes(self) -> None:
        phase = day_phase(_state())
        self.assertEqual(phase["phase"], "day-1")
        self.assertEqual(phase["votes"]["Stephanie"], "Patricia")
        self.assertEqual(phase["votes"]["Patricia"], "David")


if __name__ == "__main__":
    unittest.main()
