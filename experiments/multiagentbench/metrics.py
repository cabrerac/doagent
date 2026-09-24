"""Entropy and modularity for a retained trace.

Entropy scores how widely one fact is held.
Modularity scores whether links sit inside named groups.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence


def entropy(holder_count: int, population_size: int) -> float:
    """Return the entropy of who holds one fact.

    Args:
        holder_count: Number of participants whose record contains the fact.
        population_size: Number of participants.

    Returns:
        A score from 0 to 1.
        One holder scores 0.
        Every participant holding the fact scores 1.

    Raises:
        ValueError: The holder count is below 1, above the population size, or the population has fewer than 2 participants.
    """
    if population_size < 2:
        raise ValueError("population_size must be at least 2")
    if holder_count < 1 or holder_count > population_size:
        raise ValueError("holder_count must be between 1 and population_size")
    return math.log(holder_count) / math.log(population_size)


def modularity(
    edges: Sequence[tuple[str, str]],
    groups: Mapping[str, str],
) -> float:
    """Return the modularity of links against named groups.

    Args:
        edges: Undirected links between participants.
            Each pair is one link.
        groups: Participant name to group name.

    Returns:
        Modularity of that partition.
        One group that contains every link scores 0.

    Raises:
        ValueError: There are no links, or a link names a participant with no group.
    """
    if not edges:
        raise ValueError("modularity needs at least one link")
    degree: dict[str, int] = {}
    internal: dict[str, int] = {}
    for left, right in edges:
        if left not in groups or right not in groups:
            raise ValueError("every linked participant needs a group")
        degree[left] = degree.get(left, 0) + 1
        degree[right] = degree.get(right, 0) + 1
        if groups[left] == groups[right]:
            group = groups[left]
            internal[group] = internal.get(group, 0) + 1
    link_count = len(edges)
    group_degree: dict[str, int] = {}
    for participant, links in degree.items():
        group = groups[participant]
        group_degree[group] = group_degree.get(group, 0) + links
    score = 0.0
    for group, inside in internal.items():
        attached = group_degree.get(group, 0) / (2 * link_count)
        score += inside / link_count - attached * attached
    return score
