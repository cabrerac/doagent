"""Record one scored Hidden Profile study and its remaining measures.

The folder is the fixed run.
Every enumerated deal is already in the score, so there is no sample interval.
A view gets a calibration number only when it states the reported chances.
A view gets an action number only when each vote names one belief.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
import json
import math
from pathlib import Path
import subprocess

from experiments.information_flow.events import ActionEvent, BeliefEvent, ExecutionEvent
from experiments.information_flow.hidden_profile.breakdown import _load_views
from experiments.information_flow.hidden_profile.curves import _belief, _held, _opening
from experiments.information_flow.hidden_profile.reference import reference_report
from experiments.information_flow.hidden_profile.rules import (
    DEFAULT_CONFIG,
    HiddenProfileConfig,
    option_belief,
    run_episode,
    unique_leader,
)
from experiments.information_flow.hidden_profile.score import LABELS
from experiments.information_flow.metrics import (
    brier_score,
    conditional_entropy,
    log_loss,
    relative_entropy,
)

_SAMPLE_REASON = "Every enumerated deal is in the score."


@dataclass(frozen=True)
class ViewMeasures:
    """Calibration and action uncertainty for one view.

    Args:
        name: Short name of the view.
        label: Name used in the notes.
        relative_entropy: Mean distance from reported chances to the held-fact chances.
            None when the view does not state the chances.
        brier: Mean squared error of the reported chances.
            None when the view does not state the chances.
        log_loss: Mean log loss of the reported chances.
            None when the view does not state the chances.
        action_conditional_entropy: Uncertainty of a vote given the belief it names.
            None when a vote does not name one belief.
    """

    name: str
    label: str
    relative_entropy: float | None
    brier: float | None
    log_loss: float | None
    action_conditional_entropy: float | None


@dataclass(frozen=True)
class CampaignRecord:
    """The fixed study and the measures read from it.

    Args:
        folder: Study folder.
        record_path: Path of the written record.
        views: One row per rules view and saved view.
    """

    folder: Path
    record_path: Path
    views: tuple[ViewMeasures, ...]


def close_campaign(
    output_base: str | Path,
    config: HiddenProfileConfig = DEFAULT_CONFIG,
    deal_indexes: Sequence[int] | None = None,
    logging_levels: Sequence[int] = (0, 1, 2),
) -> CampaignRecord:
    """Write the fixed record for one saved study.

    Args:
        output_base: Directory that holds the deal folders.
        config: Hidden profile configuration.
        deal_indexes: Deals to read.
            Every enumerated deal is read when this is omitted.
        logging_levels: Session levels whose record files are read.

    Returns:
        The written record and the measure rows.

    Raises:
        ValueError: A saved deal is missing, or the correct option is missing.
    """
    folder = Path(output_base)
    report = reference_report(config)
    indexes = tuple(range(len(report.deals)) if deal_indexes is None else deal_indexes)
    correct = unique_leader(config.facts, config.options)
    if correct is None:
        raise ValueError("the complete facts must name one option")
    outcome = config.options.index(correct)
    vote_round = config.horizon - 1
    by_view: dict[str, dict[str, list[float]]] = {}
    action_pairs: dict[str, list[tuple[str, tuple[float, ...]]] | None] = {}
    for index in indexes:
        deal = report.deals[index]
        rules = run_episode(index, config, dict(deal.allocation)).events
        views = _load_views(folder / f"deal-{index}", logging_levels)
        views["rules"] = rules
        for name, events in views.items():
            _add_calibration(
                by_view.setdefault(name, {"relative_entropy": [], "brier": [], "log_loss": []}),
                events,
                rules,
                config,
                vote_round,
                outcome,
            )
            _add_actions(action_pairs, name, events)
    rows = _rows(by_view, action_pairs, config)
    record_path = folder / "campaign.json"
    _write_record(record_path, folder, indexes, logging_levels, rows)
    return CampaignRecord(folder=folder, record_path=record_path, views=rows)


def _add_calibration(
    buckets: dict[str, list[float]],
    events: Sequence[ExecutionEvent],
    rules: Sequence[ExecutionEvent],
    config: HiddenProfileConfig,
    vote_round: int,
    outcome: int,
) -> None:
    """Add one deal's chance scores when every agent states a belief."""
    opening = _opening(rules, config.agents)
    held = _held(opening, rules, config.agents, vote_round)
    scores = []
    for agent_id in config.agents:
        reported = _belief(events, agent_id, vote_round)
        if reported is None:
            return
        facts = tuple(fact for fact in config.facts if fact.fact_id in held[agent_id])
        posterior = option_belief(facts, config.options)
        ordered = _in_option_order(events, agent_id, vote_round, config.options)
        if ordered is None:
            ordered = reported
        scores.append(
            (
                relative_entropy(ordered, posterior),
                brier_score(ordered, outcome),
                log_loss(ordered, outcome),
            )
        )
    for divergence, brier, loss in scores:
        buckets["relative_entropy"].append(divergence)
        buckets["brier"].append(brier)
        buckets["log_loss"].append(loss)


def _in_option_order(
    events: Sequence[ExecutionEvent],
    agent_id: str,
    vote_round: int,
    options: Sequence[str],
) -> tuple[float, ...] | None:
    """Return one belief in option order when the file names the labels."""
    matches = [
        event
        for event in events
        if isinstance(event, BeliefEvent)
        and event.agent_id == agent_id
        and event.logical_step == vote_round
        and event.event_id == f"belief-{vote_round}-{agent_id}"
    ]
    if len(matches) != 1:
        return None
    belief = matches[0]
    if belief.state_labels != tuple(options):
        return None
    return belief.probabilities


def _add_actions(
    action_pairs: dict[str, list[tuple[str, tuple[float, ...]]] | None],
    name: str,
    events: Sequence[ExecutionEvent],
) -> None:
    """Add vote and belief pairs, or mark the view unstated."""
    if action_pairs.get(name) is None and name in action_pairs:
        return
    pairs = action_pairs.setdefault(name, [])
    if pairs is None:
        return
    beliefs = {
        event.event_id: event
        for event in events
        if isinstance(event, BeliefEvent)
    }
    for event in events:
        if not isinstance(event, ActionEvent) or not event.event_id.startswith("vote-"):
            continue
        linked = [
            item
            for item in event.input_event_ids
            if item.startswith("belief-")
        ]
        if len(linked) != 1 or linked[0] not in beliefs:
            action_pairs[name] = None
            return
        belief = beliefs[linked[0]]
        pairs.append((event.action, tuple(round(item, 6) for item in belief.probabilities)))


def _rows(
    by_view: dict[str, dict[str, list[float]]],
    action_pairs: dict[str, list[tuple[str, tuple[float, ...]]] | None],
    config: HiddenProfileConfig,
) -> tuple[ViewMeasures, ...]:
    """Return one measure row per view."""
    names = ["rules", *LABELS]
    rows = []
    for name in names:
        if name not in by_view:
            continue
        label = "Rules" if name == "rules" else LABELS[name]
        rows.append(
            ViewMeasures(
                name=name,
                label=label,
                relative_entropy=_mean(by_view[name]["relative_entropy"]),
                brier=_mean(by_view[name]["brier"]),
                log_loss=_mean(by_view[name]["log_loss"]),
                action_conditional_entropy=_action_entropy(action_pairs.get(name), config),
            )
        )
    return tuple(rows)


def _mean(values: Sequence[float]) -> float | None:
    """Return the mean, or None when the view stated nothing."""
    if not values:
        return None
    return math.fsum(values) / len(values)


def _action_entropy(
    pairs: list[tuple[str, tuple[float, ...]]] | None,
    config: HiddenProfileConfig,
) -> float | None:
    """Return the vote uncertainty given the named belief."""
    if not pairs:
        return None
    counts: Counter[tuple[str, tuple[float, ...]]] = Counter(pairs)
    signatures = sorted({signature for _action, signature in counts})
    total = sum(counts.values())
    joint = [
        [counts[(option, signature)] / total for signature in signatures]
        for option in config.options
    ]
    return conditional_entropy(joint)


def _write_record(
    path: Path,
    folder: Path,
    deals: Sequence[int],
    logging_levels: Sequence[int],
    rows: Sequence[ViewMeasures],
) -> None:
    """Write the fixed campaign record.

    Args:
        path: Destination of the record.
        folder: Study folder.
        deals: Deal indexes in the score.
        logging_levels: Session levels in the score.
        rows: Measure rows.
    """
    settings = {}
    study_path = folder / "study.json"
    if study_path.is_file():
        settings = json.loads(study_path.read_text(encoding="utf-8"))
    payload = {
        "stamp": settings.get("stamp", folder.name.removeprefix("hidden_profile_")),
        "deals": list(deals),
        "logging_levels": list(logging_levels),
        "git_commit": _git_commit(),
        "worktree_dirty": _worktree_dirty(),
        "sample_interval": None,
        "sample_interval_reason": _SAMPLE_REASON,
        "views": [
            {
                "name": row.name,
                "label": row.label,
                "relative_entropy": row.relative_entropy,
                "brier": row.brier,
                "log_loss": row.log_loss,
                "action_conditional_entropy": row.action_conditional_entropy,
            }
            for row in rows
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git_commit() -> str | None:
    """Return the current commit, or None when git cannot be read."""
    try:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[3],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    commit = value.strip()
    return commit or None


def _worktree_dirty() -> bool | None:
    """Return whether the worktree has uncommitted changes."""
    try:
        value = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=Path(__file__).resolve().parents[3],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return bool(value.strip())
