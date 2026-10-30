"""Verify labelled information channels against the delivery example."""

import math
import unittest

from experiments.information_flow.channels import build_joint_distribution
from experiments.information_flow.metrics import (
    conditional_entropy,
    mutual_information,
)


OUTCOMES = ("000", "001", "010", "011", "100", "101", "110", "111")
WEIGHTED_OUTCOMES = tuple((outcome, 1 / 8) for outcome in OUTCOMES)


class JointDistributionTests(unittest.TestCase):
    def test_count_policy_labels_the_manual_probability_matrix(self) -> None:
        distribution = build_joint_distribution(
            WEIGHTED_OUTCOMES,
            query=lambda outcome: outcome,
            recording_policy=lambda outcome: outcome.count("1"),
        )

        self.assertEqual(distribution.row_labels, OUTCOMES)
        self.assertEqual(distribution.column_labels, (0, 1, 2, 3))
        self.assertEqual(
            distribution.matrix,
            (
                (1 / 8, 0.0, 0.0, 0.0),
                (0.0, 1 / 8, 0.0, 0.0),
                (0.0, 1 / 8, 0.0, 0.0),
                (0.0, 0.0, 1 / 8, 0.0),
                (0.0, 1 / 8, 0.0, 0.0),
                (0.0, 0.0, 1 / 8, 0.0),
                (0.0, 0.0, 1 / 8, 0.0),
                (0.0, 0.0, 0.0, 1 / 8),
            ),
        )

    def test_labels_preserve_the_meaning_of_each_policy_axis(self) -> None:
        policies = (
            (
                "full",
                lambda outcome: outcome,
                OUTCOMES,
                0.0,
                3.0,
            ),
            (
                "local-a",
                lambda outcome: int(outcome[0]),
                (0, 1),
                2.0,
                1.0,
            ),
            (
                "count",
                lambda outcome: outcome.count("1"),
                (0, 1, 2, 3),
                (6 / 8) * math.log2(3),
                3.0 - (6 / 8) * math.log2(3),
            ),
        )

        for name, policy, labels, remaining, information in policies:
            with self.subTest(policy=name):
                distribution = build_joint_distribution(
                    WEIGHTED_OUTCOMES,
                    query=lambda outcome: outcome,
                    recording_policy=policy,
                )
                self.assertEqual(distribution.column_labels, labels)
                self.assertAlmostEqual(
                    conditional_entropy(distribution.matrix),
                    remaining,
                )
                self.assertAlmostEqual(
                    mutual_information(distribution.matrix),
                    information,
                )

    def test_histories_with_the_same_labels_share_one_cell(self) -> None:
        distribution = build_joint_distribution(
            (("first", 1 / 4), ("second", 3 / 4)),
            query=lambda _history: "same answer",
            recording_policy=lambda _history: "same record",
        )

        self.assertEqual(distribution.row_labels, ("same answer",))
        self.assertEqual(distribution.column_labels, ("same record",))
        self.assertEqual(distribution.matrix, ((1.0,),))

    def test_invalid_history_distribution_is_rejected(self) -> None:
        invalid_distributions = (
            (),
            (("only", 1 / 2),),
            (("negative", -1 / 2), ("large", 3 / 2)),
            (("infinite", math.inf),),
            (("not-a-number", math.nan),),
        )

        for histories in invalid_distributions:
            with self.subTest(histories=histories):
                with self.assertRaises(ValueError):
                    build_joint_distribution(
                        histories,
                        query=lambda history: history,
                        recording_policy=lambda history: history,
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
