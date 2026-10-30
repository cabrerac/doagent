"""Build labelled joint distributions for recording-policy experiments."""

from __future__ import annotations

from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
import math
from typing import Generic, TypeVar


HistoryT = TypeVar("HistoryT")
QueryT = TypeVar("QueryT", bound=Hashable)
RecordT = TypeVar("RecordT", bound=Hashable)


@dataclass(frozen=True)
class JointDistribution(Generic[QueryT, RecordT]):
    """Hold a probability matrix and the values represented by each axis."""

    row_labels: tuple[QueryT, ...]
    column_labels: tuple[RecordT, ...]
    matrix: tuple[tuple[float, ...], ...]


def build_joint_distribution(
    weighted_histories: Sequence[tuple[HistoryT, float]],
    *,
    query: Callable[[HistoryT], QueryT],
    recording_policy: Callable[[HistoryT], RecordT],
) -> JointDistribution[QueryT, RecordT]:
    """Build the joint distribution of query answers and retained records.

    Args:
        weighted_histories: Execution histories paired with their probabilities.
        query: Function that returns the true answer for one history.
        recording_policy: Function that returns the record retained for one history.

    Returns:
        A matrix whose rows are query answers and columns are retained records.
        Labels identify the value represented by each row and column.

    Raises:
        ValueError: The history distribution is empty, invalid, or does not sum to one.
    """
    histories = list(weighted_histories)
    if not histories:
        raise ValueError("weighted_histories must not be empty")
    probabilities = [probability for _history, probability in histories]
    if any(
        not math.isfinite(probability)
        or probability < 0.0
        or probability > 1.0
        for probability in probabilities
    ):
        raise ValueError("history probabilities must be finite and in the interval [0, 1]")
    if not math.isclose(
        math.fsum(probabilities),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError("history probabilities must sum to one")

    labelled_probabilities = [
        (query(history), recording_policy(history), probability)
        for history, probability in histories
    ]
    row_labels = tuple(dict.fromkeys(
        query_value
        for query_value, _record_value, _probability in labelled_probabilities
    ))
    column_labels = tuple(dict.fromkeys(
        record_value
        for _query_value, record_value, _probability in labelled_probabilities
    ))
    row_indexes = {value: index for index, value in enumerate(row_labels)}
    column_indexes = {value: index for index, value in enumerate(column_labels)}
    matrix = [
        [0.0] * len(column_labels)
        for _query_value in row_labels
    ]
    for query_value, record_value, probability in labelled_probabilities:
        row = row_indexes[query_value]
        column = column_indexes[record_value]
        matrix[row][column] += probability

    return JointDistribution(
        row_labels=row_labels,
        column_labels=column_labels,
        matrix=tuple(tuple(row) for row in matrix),
    )
