"""Calculate exact information measures for controlled experiments."""

from __future__ import annotations

import math
from collections.abc import Sequence


def self_information(probability: float) -> float:
    """Return the information in observing an outcome with the given probability.

    Args:
        probability: Probability of the observed outcome.
            The value must be greater than zero and at most one.

    Returns:
        Information in bits.

    Raises:
        ValueError: The probability is not finite or is outside the valid range.
    """
    if not math.isfinite(probability) or probability <= 0.0 or probability > 1.0:
        raise ValueError("probability must be finite and in the interval (0, 1]")
    if probability == 1.0:
        return 0.0
    return -math.log2(probability)


def shannon_entropy(probabilities: Sequence[float]) -> float:
    """Return the Shannon entropy of a discrete probability distribution.

    Args:
        probabilities: Probabilities of all outcomes in the distribution.
            The values must be finite, non-negative, and sum to one.

    Returns:
        Entropy in bits.

    Raises:
        ValueError: The distribution is empty, invalid, or does not sum to one.
    """
    values = list(probabilities)
    if not values:
        raise ValueError("probabilities must not be empty")
    if any(not math.isfinite(value) or value < 0.0 or value > 1.0 for value in values):
        raise ValueError("probabilities must be finite and in the interval [0, 1]")
    if not math.isclose(math.fsum(values), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("probabilities must sum to one")
    return math.fsum(
        probability * self_information(probability)
        for probability in values
        if probability > 0.0
    )


def conditional_entropy(joint_probabilities: Sequence[Sequence[float]]) -> float:
    """Return the average row-variable entropy after observing the column variable.

    Args:
        joint_probabilities: Joint distribution with row values as the target.
            Column values are the observed condition.

    Returns:
        Conditional entropy in bits.

    Raises:
        ValueError: The joint distribution is empty, ragged, or invalid.
    """
    rows = _validated_joint_distribution(joint_probabilities)
    column_count = len(rows[0])
    column_totals = [
        math.fsum(row[column] for row in rows)
        for column in range(column_count)
    ]
    return math.fsum(
        condition_probability
        * shannon_entropy(
            [
                row[column] / condition_probability
                for row in rows
            ]
        )
        for column, condition_probability in enumerate(column_totals)
        if condition_probability > 0.0
    )


def mutual_information(joint_probabilities: Sequence[Sequence[float]]) -> float:
    """Return the entropy reduction from observing the column variable.

    Args:
        joint_probabilities: Joint distribution of two discrete variables.
            Rows contain values of the first variable.
            Columns contain values of the second variable.

    Returns:
        Mutual information in bits.

    Raises:
        ValueError: The joint distribution is empty, ragged, or invalid.
    """
    rows = _validated_joint_distribution(joint_probabilities)
    row_totals = [math.fsum(row) for row in rows]
    return shannon_entropy(row_totals) - conditional_entropy(rows)


def brier_score(probabilities: Sequence[float], outcome_index: int) -> float:
    """Return the squared error of a reported chance list.

    The score is not in bits.
    A smaller score is closer to the outcome that happened.

    Args:
        probabilities: Reported chance of each outcome.
            The values must be finite, non-negative, and sum to one.
        outcome_index: Position of the outcome that happened.

    Returns:
        Squared error of the reported chances.

    Raises:
        ValueError: The chance list or the outcome position is not usable.
    """
    values = _validated_outcome(probabilities, outcome_index)
    return math.fsum(
        (probability - (1.0 if index == outcome_index else 0.0)) ** 2
        for index, probability in enumerate(values)
    )


def log_loss(probabilities: Sequence[float], outcome_index: int) -> float:
    """Return the information lost when a reported chance is scored.

    The result uses base-two logarithms, so the unit is bits.
    A reported chance of zero for the outcome that happened is infinite.

    Args:
        probabilities: Reported chance of each outcome.
            The values must be finite, non-negative, and sum to one.
        outcome_index: Position of the outcome that happened.

    Returns:
        Information lost, in bits.
        The value is infinite when the reported chance of the outcome is zero.

    Raises:
        ValueError: The chance list or the outcome position is not usable.
    """
    values = _validated_outcome(probabilities, outcome_index)
    probability = values[outcome_index]
    if probability == 0.0:
        return math.inf
    return self_information(probability)


def relative_entropy(
    estimate: Sequence[float],
    reference: Sequence[float],
) -> float:
    """Return how far one chance list sits from a reference chance list.

    The result is the relative entropy of the estimate from the reference.
    It uses base-two logarithms, so the unit is bits.
    The value is infinite when the estimate allows an outcome the reference rules out.

    Args:
        estimate: Reported chance of each outcome.
        reference: Reference chance of each outcome, in the same order.

    Returns:
        Relative entropy in bits.
        The value is infinite when the estimate is positive where the reference is zero.

    Raises:
        ValueError: A chance list is invalid, or the two lists differ in length.
    """
    left = list(estimate)
    right = list(reference)
    if len(left) != len(right):
        raise ValueError("estimate and reference must have the same length")
    shannon_entropy(left)
    shannon_entropy(right)
    total = 0.0
    for probability, baseline in zip(left, right, strict=True):
        if probability == 0.0:
            continue
        if baseline == 0.0:
            return math.inf
        total += probability * math.log2(probability / baseline)
    return total


def entropy_correction(support_count: int, sample_size: int) -> float:
    """Return the Miller-Madow addition for an entropy estimate.

    The addition is not clipped.
    A caller can add it to a plug-in entropy and keep a negative result.

    Args:
        support_count: How many categories the alphabet contains.
        sample_size: How many observations were counted.

    Returns:
        Correction in bits.

    Raises:
        ValueError: The support count or the sample size is not a positive integer.
    """
    if (
        isinstance(support_count, bool)
        or not isinstance(support_count, int)
        or support_count < 1
    ):
        raise ValueError("support_count must be a positive integer")
    if isinstance(sample_size, bool) or not isinstance(sample_size, int) or sample_size < 1:
        raise ValueError("sample_size must be a positive integer")
    return (support_count - 1) / (2 * sample_size * math.log(2))


def corrected_mutual_information(
    joint_probabilities: Sequence[Sequence[float]],
    sample_size: int,
) -> float:
    """Return a plug-in mutual information plus a support correction.

    The correction uses the number of categories that appear in the sample.
    The result is in bits and is not clipped.

    Args:
        joint_probabilities: Joint chances, one row per first outcome.
        sample_size: How many observations were counted.

    Returns:
        Corrected mutual information in bits.

    Raises:
        ValueError: The joint distribution or the sample size is not usable.
    """
    rows = _validated_joint_distribution(joint_probabilities)
    plugin = mutual_information(rows)
    row_support = sum(any(cell > 0.0 for cell in row) for row in rows)
    column_support = sum(
        any(row[column] > 0.0 for row in rows) for column in range(len(rows[0]))
    )
    joint_support = sum(cell > 0.0 for row in rows for cell in row)
    addition = (
        entropy_correction(row_support, sample_size)
        + entropy_correction(column_support, sample_size)
        - entropy_correction(joint_support, sample_size)
    )
    return plugin + addition


def corrected_conditional_mutual_information(
    observations: Sequence[tuple[str, str, str]],
    sample_size: int,
) -> float:
    """Return a plug-in conditional mutual information plus a support correction.

    The correction uses the number of patterns that appear in the sample.
    The result is in bits and is not clipped.

    Args:
        observations: Triples of the first field, the second field, and the condition.
        sample_size: How many observations were counted.

    Returns:
        Corrected conditional mutual information in bits.

    Raises:
        ValueError: The observations or the sample size is not usable.
    """
    plugin = conditional_mutual_information(observations)
    addition = (
        _support_correction(observations, (0, 2), sample_size)
        + _support_correction(observations, (1, 2), sample_size)
        - _support_correction(observations, (0, 1, 2), sample_size)
        - _support_correction(observations, (2,), sample_size)
    )
    return plugin + addition


def corrected_shannon_entropy(
    probabilities: Sequence[float],
    sample_size: int,
    support_count: int,
) -> float:
    """Return a plug-in entropy plus the Miller-Madow addition.

    The result is in bits.
    It is not clipped when the addition would not apply.

    Args:
        probabilities: Plug-in chance of each outcome.
        sample_size: How many observations were counted.
        support_count: How many categories the alphabet contains.

    Returns:
        Corrected entropy in bits.

    Raises:
        ValueError: The chance list, sample size, or support count is not usable.
    """
    return shannon_entropy(probabilities) + entropy_correction(support_count, sample_size)


def answer_uncertainty(candidates: Sequence[str] | None) -> float | None:
    """Return the Hartley uncertainty of a list of possible answers.

    A missing answer returns None.
    None is not a Shannon entropy.
    The list is not turned into a made-up chance distribution.

    Args:
        candidates: Possible answers, or None when the answer is missing.

    Returns:
        Ambiguity in bits, or None when the answer is missing.

    Raises:
        ValueError: The candidate list is empty or is a single text string.
    """
    if candidates is None:
        return None
    if isinstance(candidates, str):
        raise ValueError("candidates must be a list of answers")
    return hartley_ambiguity(len(candidates))


def missing_answer_rate(decoded: Sequence[str | None]) -> float:
    """Return the share of decoded answers that are missing.

    A missing answer is not counted as a Shannon category.

    Args:
        decoded: Decoded answers.
            None marks a missing answer.

    Returns:
        Share of answers that are missing.

    Raises:
        ValueError: The decoded list is empty.
    """
    if not decoded:
        raise ValueError("decoded must not be empty")
    return sum(item is None for item in decoded) / len(decoded)


def decoded_mutual_information(
    truth: Sequence[str],
    decoded: Sequence[str | None],
) -> float:
    """Return how much a decoded answer says about the true answer.

    The result is mutual information in bits.
    A missing decoded answer is refused, because it is not a Shannon category.

    Args:
        truth: True answer for each case.
        decoded: Decoded answer for each case, in the same order.

    Returns:
        Mutual information in bits.

    Raises:
        ValueError: The lists differ in length, are empty, or contain a missing answer.
    """
    if len(truth) != len(decoded) or not truth:
        raise ValueError("truth and decoded must be non-empty lists of the same length")
    if any(item is None for item in decoded):
        raise ValueError("a missing answer is not a Shannon category")
    truth_labels = list(dict.fromkeys(truth))
    decoded_labels = list(dict.fromkeys(item for item in decoded if item is not None))
    total = len(truth)
    counts: dict[tuple[str, str], int] = {}
    for true_label, decoded_label in zip(truth, decoded, strict=True):
        if decoded_label is None:
            continue
        key = (true_label, decoded_label)
        counts[key] = counts.get(key, 0) + 1
    matrix = [
        [counts.get((left, right), 0) / total for right in decoded_labels]
        for left in truth_labels
    ]
    return mutual_information(matrix)


def conditional_mutual_information(
    observations: Sequence[tuple[str, str, str]],
) -> float:
    """Return how much the first field says about the second, given the third.

    Each observation is one equally likely triple.
    The result is conditional mutual information in bits.

    Args:
        observations: Triples of the first field, the second field, and the condition.

    Returns:
        Conditional mutual information in bits.

    Raises:
        ValueError: The observation list is empty.
    """
    if not observations:
        raise ValueError("observations must not be empty")
    total = len(observations)
    return (
        _pair_entropy(observations, (0, 2), total)
        + _pair_entropy(observations, (1, 2), total)
        - _pair_entropy(observations, (0, 1, 2), total)
        - _pair_entropy(observations, (2,), total)
    )


def hartley_ambiguity(candidate_count: int) -> float:
    """Return the uncertainty among equally possible candidate answers.

    Args:
        candidate_count: Number of candidate answers.
            The value must be a positive integer.

    Returns:
        Ambiguity in bits.

    Raises:
        ValueError: The candidate count is not a positive integer.
    """
    if (
        isinstance(candidate_count, bool)
        or not isinstance(candidate_count, int)
        or candidate_count < 1
    ):
        raise ValueError("candidate_count must be a positive integer")
    return math.log2(candidate_count)


def _validated_outcome(
    probabilities: Sequence[float],
    outcome_index: int,
) -> list[float]:
    """Return a chance list when the outcome position names one of its entries."""
    values = list(probabilities)
    shannon_entropy(values)
    if isinstance(outcome_index, bool) or not isinstance(outcome_index, int):
        raise ValueError("outcome_index must name one outcome")
    if outcome_index < 0 or outcome_index >= len(values):
        raise ValueError("outcome_index must name one outcome")
    return values


def _support_correction(
    observations: Sequence[tuple[str, str, str]],
    fields: tuple[int, ...],
    sample_size: int,
) -> float:
    """Return the entropy correction for the named fields."""
    keys = {tuple(observation[field] for field in fields) for observation in observations}
    return entropy_correction(len(keys), sample_size)


def _pair_entropy(
    observations: Sequence[tuple[str, str, str]],
    fields: tuple[int, ...],
    total: int,
) -> float:
    """Return the entropy of the named fields in a list of triples."""
    counts: dict[tuple[str, ...], int] = {}
    for observation in observations:
        key = tuple(observation[field] for field in fields)
        counts[key] = counts.get(key, 0) + 1
    probabilities = [count / total for count in counts.values()]
    probabilities[-1] += 1.0 - math.fsum(probabilities)
    return shannon_entropy(probabilities)


def _validated_joint_distribution(
    joint_probabilities: Sequence[Sequence[float]],
) -> list[list[float]]:
    """Return a rectangular joint distribution whose values sum to one."""
    rows = [list(row) for row in joint_probabilities]
    if not rows or not rows[0]:
        raise ValueError("joint_probabilities must not be empty")
    column_count = len(rows[0])
    if any(len(row) != column_count for row in rows):
        raise ValueError("joint_probabilities must be rectangular")
    values = [value for row in rows for value in row]
    if any(not math.isfinite(value) or value < 0.0 or value > 1.0 for value in values):
        raise ValueError(
            "joint probabilities must be finite and in the interval [0, 1]"
        )
    if not math.isclose(math.fsum(values), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("joint probabilities must sum to one")
    return rows
