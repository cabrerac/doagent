"""Rebuild entropy and modularity from participant logs.

A fact missing from every log counts as a total miss.
A participant with no vote line counts as a total miss.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from experiments.multiagentbench.metrics import entropy, modularity

VOTE_MARKER = "voted for "


def player_logs(directory: Path) -> dict[str, str]:
    """Return each participant log in a game directory.

    Args:
        directory: Directory that holds the per-participant log files.

    Returns:
        Participant name to the full log text.
    """
    logs = {}
    for path in directory.glob("*_log.txt"):
        stem = path.name[: -len("_log.txt")]
        parts = stem.split("-", 2)
        if len(parts) < 3:
            continue
        logs[parts[2]] = path.read_text(encoding="utf-8")
    return logs


def slice_log(text: str, phase: str) -> str:
    """Return the log text for one night or one day.

    Args:
        text: Full log for one participant.
        phase: Phase name such as night-1 or day-2.

    Returns:
        The text from that phase start up to the next phase start.
        An empty string when the phase marker is absent.
    """
    kind, number_text = phase.split("-", 1)
    number = int(number_text)
    if kind == "night":
        start_marker = f"Night {number} begins"
        end_marker = f"Day {number} begins"
    else:
        start_marker = f"Day {number} begins"
        end_marker = f"Night {number + 1} begins"
    start = text.find(start_marker)
    if start < 0:
        return ""
    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        return text[start:]
    return text[start:end]


def logs_for_phases(
    directory: Path,
    phases: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, str]]:
    """Return participant logs sliced to each phase.

    Args:
        directory: Directory that holds the per-participant log files.
        phases: Truth phases, each with a phase name.

    Returns:
        Phase name to participant name to that phase's log text.
    """
    full = player_logs(directory)
    sliced = {}
    for phase in phases:
        name = phase["phase"]
        sliced[name] = {player: slice_log(text, name) for player, text in full.items()}
    return sliced


def write_gap(path: Path, gaps: Mapping[str, Optional[float]]) -> None:
    """Write entropy and modularity gaps as JSON.

    Args:
        path: Destination file.
        gaps: Gap values from compare.
    """
    path.write_text(json.dumps(gaps, indent=2), encoding="utf-8")


def modularity_of(choices: Mapping[str, str]) -> float:
    """Return modularity for participants who share a choice.

    Args:
        choices: Participant name to chosen label.

    Returns:
        Modularity of the cliques formed by equal choices.

    Raises:
        ValueError: Fewer than two participants made a choice.
    """
    if len(choices) < 2:
        raise ValueError("modularity needs at least two choices")
    groups = dict(choices)
    names = list(choices)
    edges = []
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            if choices[left] == choices[right]:
                edges.append((left, right))
    if not edges:
        raise ValueError("modularity needs at least one link")
    return modularity(edges, groups)


def entropy_from_logs(
    logs: Mapping[str, str],
    fact_name: str,
    population_size: int,
) -> Optional[float]:
    """Return the entropy of a fact as it appears in the logs.

    Args:
        logs: Participant name to that participant's log text.
        fact_name: Text that counts as holding the fact.
        population_size: Number of participants in the phase.

    Returns:
        The entropy of the participants whose log contains the fact name.
        None when no log contains the fact name.
    """
    holders = [name for name, text in logs.items() if fact_name in text]
    if not holders:
        return None
    return entropy(len(holders), population_size)


def choices_from_logs(
    logs: Mapping[str, str],
    participants: Sequence[str],
) -> Optional[dict[str, str]]:
    """Return each participant's vote as written in that participant's log.

    Args:
        logs: Participant name to that participant's log text.
        participants: Participants who voted in the truth file.

    Returns:
        Participant name to vote label.
        None when any of those logs has no vote line.
    """
    choices: dict[str, str] = {}
    for name in participants:
        text = logs.get(name, "")
        marker = f"{name} {VOTE_MARKER}"
        marker_at = text.rfind(marker)
        if marker_at < 0:
            return None
        choice = text[marker_at + len(marker) :].split()[0]
        choices[name] = choice
    return choices


def mean_gap(
    truth_scores: Sequence[float],
    recovered_scores: Sequence[Optional[float]],
) -> float:
    """Return the mean distance between a truth curve and a recovered curve.

    Args:
        truth_scores: Scores from the truth file, in phase order.
        recovered_scores: Scores from the logs, in the same order.
            None is a total miss.

    Returns:
        The mean absolute distance.
        A missing recovered score contributes 1.

    Raises:
        ValueError: The two sequences differ in length, or both are empty.
    """
    if len(truth_scores) != len(recovered_scores):
        raise ValueError("truth and recovered curves must have the same length")
    if not truth_scores:
        raise ValueError("a gap needs at least one score")
    distances = []
    for truth_score, recovered_score in zip(truth_scores, recovered_scores):
        if recovered_score is None:
            distances.append(1.0)
        else:
            distances.append(abs(truth_score - recovered_score))
    return sum(distances) / len(distances)


def compare(
    truth: Mapping[str, object],
    logs_by_phase: Mapping[str, Mapping[str, str]],
) -> dict[str, Optional[float]]:
    """Return the entropy gap and the modularity gap for one game.

    Args:
        truth: Truth document with a list of phases.
        logs_by_phase: Phase name to participant logs.
            Recovered scores are computed from these logs only.

    Returns:
        A dictionary with entropy_gap and modularity_gap.
        modularity_gap is None when the truth file has no votes.
    """
    phases = truth["phases"]
    entropy_truth: list[float] = []
    entropy_recovered: list[Optional[float]] = []
    modularity_truth: list[float] = []
    modularity_recovered: list[Optional[float]] = []
    for phase in phases:
        logs = logs_by_phase[phase["phase"]]
        population_size = phase["population_size"]
        for fact in phase.get("facts", []):
            holders = fact["holders"]
            entropy_truth.append(entropy(len(holders), population_size))
            entropy_recovered.append(
                entropy_from_logs(logs, fact["name"], population_size)
            )
        votes = phase.get("votes")
        if not votes:
            continue
        modularity_truth.append(modularity_of(votes))
        found = choices_from_logs(logs, list(votes))
        if found is None:
            modularity_recovered.append(None)
        else:
            modularity_recovered.append(modularity_of(found))
    entropy_gap = mean_gap(entropy_truth, entropy_recovered) if entropy_truth else None
    modularity_gap = (
        mean_gap(modularity_truth, modularity_recovered) if modularity_truth else None
    )
    return {"entropy_gap": entropy_gap, "modularity_gap": modularity_gap}
