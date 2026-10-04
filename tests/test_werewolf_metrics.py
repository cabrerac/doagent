"""Entropy and modularity on a fixed Werewolf night."""

import unittest

from experiments.multiagentbench.episode_curve import FactBook
from experiments.multiagentbench.metrics import entropy, modularity
from experiments.multiagentbench.recover import line_span, recover_curve

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

    def test_missing_audience_scores_zero(self) -> None:
        self.assertEqual(entropy(0, POPULATION), 0.0)
        self.assertEqual(entropy(1, 1), 0.0)


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


class FactBookTests(unittest.TestCase):
    def test_holder_death_lowers_entropy_and_non_holder_death_raises_it(self) -> None:
        players = [f"p{index}" for index in range(9)]
        book = FactBook(players)
        book.create("night-1", "target Ethel", players[:3])
        book.close_night("night-1")
        self.assertAlmostEqual(book.episodes[0]["game_entropy"], 0.5)
        book.remove("p0")
        book.close_night("night-2")
        self.assertEqual(len(book.episodes[1]["audience"]), 8)
        self.assertAlmostEqual(book.episodes[1]["facts"][0]["entropy"], entropy(2, 8))
        other = FactBook(players)
        other.create("night-1", "target Ethel", players[:3])
        other.remove("p8")
        other.close_night("night-1")
        self.assertAlmostEqual(other.episodes[0]["facts"][0]["entropy"], entropy(3, 8))

    def test_last_holder_scores_zero(self) -> None:
        book = FactBook(["wolf", "seer"])
        book.create("night-1", "target Ethel", ["wolf"])
        book.remove("wolf")
        book.close_night("night-1")
        self.assertEqual(book.episodes[0]["game_entropy"], 0.0)

    def test_same_words_stay_separate_facts(self) -> None:
        book = FactBook(["Heather", "Jose", "Marie"])
        book.create("night-1", "Final Target: Christine", ["Heather", "Jose"])
        book.deliver("Final Target: Christine", ["Heather", "Jose"])
        book.close_night("night-1")
        book.create("night-2", "Final Target: Christine", ["Heather"])
        book.close_night("night-2")
        self.assertEqual(len(book.episodes[1]["facts"]), 2)
        self.assertEqual(book.episodes[1]["facts"][0]["origin"], "night-1")
        self.assertEqual(book.episodes[1]["facts"][1]["origin"], "night-2")
        self.assertAlmostEqual(
            book.episodes[1]["game_entropy"],
            (
                book.episodes[1]["facts"][0]["entropy"]
                + book.episodes[1]["facts"][1]["entropy"]
            )
            / 2,
        )

    def test_one_vote_has_no_modularity_point(self) -> None:
        book = FactBook(["a", "b", "c"])
        book.close_day("day-1", {"a": "abstain"})
        self.assertIsNone(book.episodes[0]["modularity"])

    def test_recovery_ignores_text_from_before_the_fact(self) -> None:
        players = ["Heather", "Jose", "Marie"]
        book = FactBook(players)
        book.create("night-1", "Final Target: Christine", ["Heather"])
        book.deliver("Final Target: Christine", ["Heather"])
        book.close_night("night-1")
        book.create("night-2", "Final Target: Christine", ["Jose"])
        book.deliver("Final Target: Christine", ["Jose"])
        book.close_night("night-2")
        document = book.document()
        lines = [
            {"content": "Final Target: Christine", "recipients": ["Heather"]},
            {"content": "Final Target: Christine", "recipients": ["Jose"]},
        ]

        def text_for(origin: str, current: str, player_id: str) -> str:
            start, end = line_span(document["episodes"], origin, current)
            parts = []
            for line in lines[start:end]:
                if player_id in line["recipients"]:
                    parts.append(line["content"])
            return "\n".join(parts)

        recovered = recover_curve(document, text_for, {})
        self.assertAlmostEqual(
            recovered[1]["game_entropy"],
            document["episodes"][1]["game_entropy"],
        )
        night_two = document["episodes"][1]["facts"][1]
        self.assertEqual(night_two["holders"], ["Jose"])


if __name__ == "__main__":
    unittest.main()
