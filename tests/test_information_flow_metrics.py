"""Verify exact information measures against hand calculations."""

import math
import unittest

from experiments.information_flow.metrics import (
    answer_uncertainty,
    brier_score,
    conditional_entropy,
    conditional_mutual_information,
    corrected_conditional_mutual_information,
    corrected_mutual_information,
    corrected_shannon_entropy,
    decoded_mutual_information,
    entropy_correction,
    hartley_ambiguity,
    log_loss,
    missing_answer_rate,
    mutual_information,
    relative_entropy,
    self_information,
    shannon_entropy,
)

OUTCOMES = ("000", "001", "010", "011", "100", "101", "110", "111")


def _deterministic_joint_table(labels: list[int], label_count: int) -> list[list[float]]:
    """Return the uniform outcome distribution joined with deterministic labels."""
    probability = 1 / len(labels)
    table = [[0.0] * label_count for _label in labels]
    for row, label in enumerate(labels):
        table[row][label] = probability
    return table


class SelfInformationTests(unittest.TestCase):
    def test_certain_outcome_contains_no_information(self) -> None:
        self.assertEqual(self_information(1.0), 0.0)

    def test_one_of_eight_outcomes_contains_three_bits(self) -> None:
        self.assertEqual(self_information(1 / 8), 3.0)

    def test_biased_protocol_outcomes_have_different_information(self) -> None:
        self.assertAlmostEqual(self_information(3 / 4), 0.4150374992788438)
        self.assertEqual(self_information(1 / 4), 2.0)

    def test_invalid_probability_is_rejected(self) -> None:
        for probability in (0.0, -0.1, 1.1, math.inf, math.nan):
            with self.subTest(probability=probability):
                with self.assertRaises(ValueError):
                    self_information(probability)


class ShannonEntropyTests(unittest.TestCase):
    def test_uniform_eight_outcomes_have_three_bits(self) -> None:
        self.assertEqual(shannon_entropy([1 / 8] * 8), 3.0)

    def test_biased_protocol_has_expected_entropy(self) -> None:
        expected = (3 / 4) * self_information(3 / 4)
        expected += (1 / 4) * self_information(1 / 4)
        self.assertAlmostEqual(shannon_entropy([3 / 4, 1 / 4]), expected)
        self.assertAlmostEqual(expected, 0.8112781244591328)

    def test_impossible_outcome_contributes_nothing(self) -> None:
        self.assertEqual(shannon_entropy([1.0, 0.0]), 0.0)

    def test_invalid_distribution_is_rejected(self) -> None:
        invalid_distributions = (
            [],
            [0.2, 0.2],
            [-0.1, 1.1],
            [math.inf, 0.0],
            [math.nan, 1.0],
        )
        for probabilities in invalid_distributions:
            with self.subTest(probabilities=probabilities):
                with self.assertRaises(ValueError):
                    shannon_entropy(probabilities)


class HartleyAmbiguityTests(unittest.TestCase):
    def test_candidate_counts_match_delivery_example(self) -> None:
        expected = {1: 0.0, 3: math.log2(3), 4: 2.0, 8: 3.0}
        for candidate_count, bits in expected.items():
            with self.subTest(candidate_count=candidate_count):
                self.assertAlmostEqual(hartley_ambiguity(candidate_count), bits)

    def test_count_policy_information_gain_matches_manual_value(self) -> None:
        initial_uncertainty = shannon_entropy([1 / 8] * 8)
        remaining_uncertainty = hartley_ambiguity(3)
        information_gain = initial_uncertainty - remaining_uncertainty
        self.assertAlmostEqual(information_gain, self_information(3 / 8))
        self.assertAlmostEqual(information_gain, 1.415037499278844)

    def test_invalid_candidate_count_is_rejected(self) -> None:
        for candidate_count in (0, -1, 1.5, True):
            with self.subTest(candidate_count=candidate_count):
                with self.assertRaises(ValueError):
                    hartley_ambiguity(candidate_count)


class ConditionalEntropyTests(unittest.TestCase):
    def test_full_policy_leaves_no_uncertainty(self) -> None:
        table = _deterministic_joint_table(list(range(8)), 8)
        self.assertEqual(conditional_entropy(table), 0.0)

    def test_local_a_policy_leaves_two_bits(self) -> None:
        labels = [int(outcome[0]) for outcome in OUTCOMES]
        table = _deterministic_joint_table(labels, 2)
        self.assertEqual(conditional_entropy(table), 2.0)

    def test_count_policy_matches_weighted_manual_value(self) -> None:
        labels = [outcome.count("1") for outcome in OUTCOMES]
        table = _deterministic_joint_table(labels, 4)
        expected = (6 / 8) * math.log2(3)
        self.assertAlmostEqual(conditional_entropy(table), expected)
        self.assertAlmostEqual(expected, 1.188721875540867)

    def test_independent_observation_leaves_one_bit(self) -> None:
        table = [[1 / 4, 1 / 4], [1 / 4, 1 / 4]]
        self.assertEqual(conditional_entropy(table), 1.0)


class MutualInformationTests(unittest.TestCase):
    def test_full_policy_provides_three_bits(self) -> None:
        table = _deterministic_joint_table(list(range(8)), 8)
        self.assertEqual(mutual_information(table), 3.0)

    def test_local_a_policy_provides_one_bit(self) -> None:
        labels = [int(outcome[0]) for outcome in OUTCOMES]
        table = _deterministic_joint_table(labels, 2)
        self.assertEqual(mutual_information(table), 1.0)

    def test_count_policy_matches_entropy_reduction(self) -> None:
        labels = [outcome.count("1") for outcome in OUTCOMES]
        table = _deterministic_joint_table(labels, 4)
        remaining = conditional_entropy(table)
        information = mutual_information(table)
        self.assertAlmostEqual(information, 3.0 - remaining)
        self.assertAlmostEqual(information, 1.811278124459133)

    def test_independent_variables_have_no_mutual_information(self) -> None:
        table = [[1 / 4, 1 / 4], [1 / 4, 1 / 4]]
        self.assertEqual(mutual_information(table), 0.0)

    def test_perfectly_correlated_bits_share_one_bit(self) -> None:
        table = [[1 / 2, 0.0], [0.0, 1 / 2]]
        self.assertEqual(conditional_entropy(table), 0.0)
        self.assertEqual(mutual_information(table), 1.0)

    def test_invalid_joint_distribution_is_rejected(self) -> None:
        invalid_distributions = (
            [],
            [[]],
            [[1 / 2], [1 / 4, 1 / 4]],
            [[1 / 4, 1 / 4]],
            [[-1 / 2, 3 / 2]],
            [[math.inf, 0.0]],
            [[math.nan, 1.0]],
        )
        for probabilities in invalid_distributions:
            with self.subTest(probabilities=probabilities):
                with self.assertRaises(ValueError):
                    conditional_entropy(probabilities)
                with self.assertRaises(ValueError):
                    mutual_information(probabilities)


class CalibrationTests(unittest.TestCase):
    def test_brier_score_matches_hand_calculation(self) -> None:
        score = brier_score((0.5, 0.25, 0.25), 0)
        self.assertAlmostEqual(score, 0.375)

    def test_log_loss_matches_hand_calculation(self) -> None:
        self.assertEqual(log_loss((0.5, 0.25, 0.25), 0), 1.0)
        self.assertEqual(log_loss((0.5, 0.25, 0.25), 1), 2.0)

    def test_zero_chance_makes_log_loss_infinite(self) -> None:
        self.assertTrue(math.isinf(log_loss((1.0, 0.0), 1)))

    def test_relative_entropy_of_matching_chances_is_zero(self) -> None:
        chances = (0.5, 0.25, 0.25)
        self.assertEqual(relative_entropy(chances, chances), 0.0)

    def test_relative_entropy_matches_hand_calculation(self) -> None:
        estimate = (0.5, 0.5)
        reference = (0.9, 0.1)
        expected = 0.5 * math.log2(0.5 / 0.9)
        expected += 0.5 * math.log2(0.5 / 0.1)
        self.assertAlmostEqual(relative_entropy(estimate, reference), expected)
        self.assertAlmostEqual(expected, 0.7369655941662062)

    def test_relative_entropy_is_infinite_when_the_reference_rules_an_outcome_out(self) -> None:
        self.assertTrue(math.isinf(relative_entropy((0.5, 0.5), (1.0, 0.0))))

    def test_invalid_calibration_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            brier_score((0.5, 0.5), 2)
        with self.assertRaises(ValueError):
            log_loss((0.5, 0.5), True)
        with self.assertRaises(ValueError):
            relative_entropy((0.5, 0.5), (1.0,))


class CorrectionTests(unittest.TestCase):
    def test_miller_madow_addition_matches_hand_calculation(self) -> None:
        addition = entropy_correction(2, 100)
        self.assertAlmostEqual(addition, 1 / (200 * math.log(2)))
        self.assertAlmostEqual(addition, 0.007213475204444108)

    def test_corrected_entropy_adds_the_correction_without_clipping(self) -> None:
        corrected = corrected_shannon_entropy((0.5, 0.5), 2, 2)
        self.assertAlmostEqual(corrected, 1.0 + entropy_correction(2, 2))
        self.assertGreater(corrected, 1.0)

    def test_mutual_information_correction_uses_observed_support(self) -> None:
        matrix = ((0.5, 0.0), (0.0, 0.5))
        addition = entropy_correction(2, 100)
        corrected = corrected_mutual_information(matrix, 100)
        self.assertAlmostEqual(corrected, mutual_information(matrix) + addition)

    def test_conditional_correction_uses_observed_support(self) -> None:
        observations = (("0", "0", "z"), ("1", "1", "z"))
        corrected = corrected_conditional_mutual_information(observations, 2)
        self.assertAlmostEqual(corrected, 1.0 + entropy_correction(2, 2))


class AnswerTreatmentTests(unittest.TestCase):
    def test_missing_answer_has_no_bit_count(self) -> None:
        self.assertIsNone(answer_uncertainty(None))
        self.assertEqual(missing_answer_rate(("hill", None, None)), 2 / 3)

    def test_candidate_list_uses_hartley_not_a_made_up_distribution(self) -> None:
        candidates = ("route-hill", "route-tunnel", "route-bridge", "route-other")
        self.assertEqual(answer_uncertainty(candidates), 2.0)
        self.assertEqual(answer_uncertainty(candidates), hartley_ambiguity(4))

    def test_a_text_string_is_not_a_candidate_list(self) -> None:
        with self.assertRaises(ValueError):
            answer_uncertainty("hill")

    def test_matching_decoded_answers_keep_the_truth_entropy(self) -> None:
        truth = ("hill", "hill", "tunnel", "tunnel")
        self.assertAlmostEqual(decoded_mutual_information(truth, truth), 1.0)

    def test_missing_decoded_answer_is_not_a_shannon_category(self) -> None:
        with self.assertRaises(ValueError):
            decoded_mutual_information(("hill", "tunnel"), ("hill", None))


class ConditionalMutualInformationTests(unittest.TestCase):
    def test_perfect_link_given_a_constant_condition_is_one_bit(self) -> None:
        observations = (("0", "0", "z"), ("1", "1", "z"))
        self.assertEqual(conditional_mutual_information(observations), 1.0)

    def test_independent_fields_share_nothing(self) -> None:
        observations = (
            ("0", "0", "z"),
            ("0", "1", "z"),
            ("1", "0", "z"),
            ("1", "1", "z"),
        )
        self.assertEqual(conditional_mutual_information(observations), 0.0)

    def test_empty_observations_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            conditional_mutual_information(())


if __name__ == "__main__":
    unittest.main(verbosity=2)
