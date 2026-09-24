"""Entropy and modularity on a fixed Werewolf night."""

import unittest

from experiments.multiagentbench.metrics import entropy, modularity

POPULATION = 9


def _clique(participants: list[str]) -> list[tuple[str, str]]:
    links = []
    for index, left in enumerate(participants):
        for right in participants[index + 1 :]:
            links.append((left, right))
    return links


class EntropyTests(unittest.TestCase):
    def test_night_one_audiences(self) -> None:
        self.assertEqual(entropy(1, POPULATION), 0.0)
        self.assertEqual(entropy(3, POPULATION), 0.5)
        self.assertEqual(entropy(POPULATION, POPULATION), 1.0)

    def test_missing_audience_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            entropy(0, POPULATION)


class ModularityTests(unittest.TestCase):
    def test_two_vote_groups(self) -> None:
        villagers = ["Nicole", "Stephanie", "John", "David", "Mary", "Sandra"]
        wolves = ["Patricia", "Jami", "Priscilla"]
        groups = {name: "village" for name in villagers}
        groups.update({name: "wolf" for name in wolves})
        edges = _clique(villagers) + _clique(wolves)
        self.assertAlmostEqual(modularity(edges, groups), 5 / 18)

    def test_one_group_scores_zero(self) -> None:
        participants = [
            "Patricia",
            "Nicole",
            "Stephanie",
            "John",
            "David",
            "Mary",
            "Sandra",
            "Jami",
            "Priscilla",
        ]
        groups = {name: "village" for name in participants}
        self.assertEqual(modularity(_clique(participants), groups), 0.0)

    def test_one_vote_has_no_links(self) -> None:
        with self.assertRaises(ValueError):
            modularity([], {"Stephanie": "village"})


if __name__ == "__main__":
    unittest.main()
