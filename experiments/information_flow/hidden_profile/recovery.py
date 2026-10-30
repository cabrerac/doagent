"""Plot remaining question uncertainty at each logical step.

The rules, read up to that step, are the reference curve.
A saved view recovers a drop when its files state the same answer.
Questions without a short list of possible answers stay off this figure.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import json
import math
from pathlib import Path

from experiments.information_flow.events import ExecutionEvent
from experiments.information_flow.hidden_profile.breakdown import (
    _belief_links,
    _load_views,
    _recipient,
)
from experiments.information_flow.hidden_profile.compare import _bridge_message_id
from experiments.information_flow.hidden_profile.reference import reference_report
from experiments.information_flow.hidden_profile.rules import (
    DEFAULT_CONFIG,
    HiddenProfileConfig,
    run_episode,
)
from experiments.information_flow.hidden_profile.score import LABELS
from experiments.information_flow.queries import Answer, decode

_DIMENSIONS = ("Accountability", "Traceability", "Explainability")


@dataclass(frozen=True)
class RecoveryPoint:
    """One average uncertainty at one step.

    Args:
        dimension: Accountability, traceability, or explainability.
        step: Logical step.
        view: Rules or a saved view.
        label: Name used on the plot.
        bits: Average remaining uncertainty.
    """

    dimension: str
    step: int
    view: str
    label: str
    bits: float


@dataclass(frozen=True)
class RecoveryReport:
    """The recovery curves and the figure path.

    Args:
        deals: How many deals were read.
        steps: Logical steps, in order.
        points: One average per dimension, step, and view.
        table_path: Path of the written table.
        plot_path: Path of the written figure.
    """

    deals: int
    steps: tuple[int, ...]
    points: tuple[RecoveryPoint, ...]
    table_path: Path
    plot_path: Path


def remaining_bits(rules_answer: Answer, view_answer: Answer, prior: float) -> float:
    """Return the uncertainty a view still has about one question.

    The height stays at the prior until the rules state an answer.
    It drops to zero when the view states that same answer.

    Args:
        rules_answer: Answer from the rules prefix.
        view_answer: Answer from one saved view at the same step.
        prior: Uncertainty while the answer is still open.

    Returns:
        Remaining uncertainty in bits.

    Raises:
        ValueError: The prior is not a positive finite number.
    """
    if not math.isfinite(prior) or prior <= 0.0:
        raise ValueError("prior must be a positive finite number")
    if rules_answer.kind != "exact" or view_answer != rules_answer:
        return prior
    return 0.0


def plot_recovery(
    output_base: str | Path,
    config: HiddenProfileConfig = DEFAULT_CONFIG,
    deal_indexes: Sequence[int] | None = None,
    logging_levels: Sequence[int] = (0, 1, 2),
) -> RecoveryReport:
    """Read a saved study and write the recovery curves.

    Args:
        output_base: Directory that holds the deal folders.
        config: Hidden profile configuration.
        deal_indexes: Deals to read.
            Every enumerated deal is read when this is omitted.
        logging_levels: Session levels whose record files are read.

    Returns:
        The averages and the figure path.

    Raises:
        ValueError: A saved deal is missing.
    """
    folder = Path(output_base)
    report = reference_report(config)
    indexes = tuple(range(len(report.deals)) if deal_indexes is None else deal_indexes)
    totals: dict[tuple[str, int, str], list[float]] = {}
    steps: set[int] = set()
    for index in indexes:
        deal = report.deals[index]
        rules = run_episode(index, config, dict(deal.allocation)).events
        deal_steps = _steps(rules)
        steps.update(deal_steps)
        message_id = _bridge_message_id(rules, report.bridge_fact_id)
        recipient = _recipient(rules, message_id)
        questions = _timed_questions(config, report.bridge_fact_id, message_id, recipient)
        views = _load_views(folder / f"deal-{index}", logging_levels)
        views["rules"] = rules
        for step in deal_steps:
            prefixes = {
                name: _prefix(events, step)
                for name, events in views.items()
            }
            for question in questions:
                truth = question.answer(prefixes["rules"])
                for name, events in prefixes.items():
                    answer = truth if name == "rules" else question.answer(events)
                    totals.setdefault((question.dimension, step, name), []).append(
                        remaining_bits(truth, answer, question.prior)
                    )
    ordered_steps = tuple(sorted(steps))
    points = _averages(totals)
    table_path = folder / "recovery.json"
    plot_path = folder / "recovery.png"
    _write_table(table_path, len(indexes), ordered_steps, points)
    _write_plot(plot_path, ordered_steps, points)
    return RecoveryReport(
        deals=len(indexes),
        steps=ordered_steps,
        points=points,
        table_path=table_path,
        plot_path=plot_path,
    )


@dataclass(frozen=True)
class _TimedQuestion:
    """One question with a declared starting height."""

    dimension: str
    label: str
    prior: float
    answer: Callable[[Sequence[ExecutionEvent]], Answer]


def _timed_questions(
    config: HiddenProfileConfig,
    bridge_fact_id: str,
    message_id: str,
    recipient: str,
) -> tuple[_TimedQuestion, ...]:
    """Return the questions whose open answers have a short list."""
    agent_bits = math.log2(len(config.agents))
    route_bits = math.log2(len(config.options))
    message_bits = math.log2(config.horizon * len(config.agents))
    vote_set_bits = float(len(config.agents))
    rows = [
        _TimedQuestion(
            "Accountability",
            "Who sent the bridge fact?",
            agent_bits,
            lambda events: decode(events, "sender", event_id=message_id),
        ),
        _TimedQuestion(
            "Accountability",
            "Who received the bridge fact?",
            agent_bits,
            lambda events: decode(events, "recipients", event_id=message_id),
        ),
        _TimedQuestion(
            "Traceability",
            "Which message first brought the bridge fact to its recipient?",
            message_bits,
            lambda events: decode(
                events,
                "first_access",
                fact_id=bridge_fact_id,
                agent_id=recipient,
            ),
        ),
    ]
    for agent_id in config.agents:
        rows.append(
            _TimedQuestion(
                "Accountability",
                f"What did {agent_id} vote?",
                route_bits,
                lambda events, agent_id=agent_id: decode(
                    events,
                    "decision_action",
                    event_id=f"vote-{agent_id}",
                ),
            )
        )
    rows.append(
        _TimedQuestion(
            "Accountability",
            "Which votes produced the group choice?",
            vote_set_bits,
            lambda events: decode(events, "group_votes", event_id="outcome-group"),
        )
    )
    rows.append(
        _TimedQuestion(
            "Traceability",
            "Does each vote point at the reported chances?",
            1.0,
            lambda events: _belief_links(events, config.agents),
        )
    )
    for agent_id in config.agents:
        rows.append(
            _TimedQuestion(
                "Explainability",
                f"Did {agent_id} vote for the top chance?",
                1.0,
                lambda events, agent_id=agent_id: decode(
                    events,
                    "vote_matches_chances",
                    event_id=f"vote-{agent_id}",
                ),
            )
        )
    return tuple(rows)


def _steps(events: Sequence[ExecutionEvent]) -> tuple[int, ...]:
    """Return the logical steps in one episode."""
    return tuple(sorted({event.logical_step for event in events}))


def _prefix(events: Sequence[ExecutionEvent], step: int) -> tuple[ExecutionEvent, ...]:
    """Return the events at or before one logical step."""
    return tuple(event for event in events if event.logical_step <= step)


def _averages(
    totals: dict[tuple[str, int, str], list[float]],
) -> tuple[RecoveryPoint, ...]:
    """Return the mean uncertainty for each dimension, step, and view."""
    points = []
    for (dimension, step, view), values in totals.items():
        label = "Rules" if view == "rules" else LABELS[view]
        points.append(
            RecoveryPoint(
                dimension=dimension,
                step=step,
                view=view,
                label=label,
                bits=math.fsum(values) / len(values),
            )
        )
    return tuple(points)


def _write_table(
    path: Path,
    deals: int,
    steps: Sequence[int],
    points: Sequence[RecoveryPoint],
) -> None:
    """Write the recovery table.

    Args:
        path: Destination of the table.
        deals: How many deals were read.
        steps: Logical steps, in order.
        points: Averages to store.
    """
    payload = {
        "deals": deals,
        "steps": list(steps),
        "points": [
            {
                "dimension": point.dimension,
                "step": point.step,
                "view": point.view,
                "label": point.label,
                "bits": point.bits,
            }
            for point in points
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_plot(
    path: Path,
    steps: Sequence[int],
    points: Sequence[RecoveryPoint],
) -> None:
    """Save one recovery curve for each dimension.

    Views that follow the same points in a panel share one line.

    Args:
        path: Destination of the figure.
        steps: Logical steps, in order.
        points: Averages to draw.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 3, figsize=(12, 4.8), sharey=True)
    labels = _step_labels(steps)
    ceiling = max(point.bits for point in points)
    colors = ("#4C78A8", "#F58518", "#E45756", "#54A24B", "#B279A2")
    for axis, dimension in zip(axes, _DIMENSIONS):
        color_index = 0
        for views, series in _curve_groups(points, dimension, steps):
            legend = _group_label(views)
            if "rules" in views:
                axis.plot(
                    range(len(steps)),
                    series,
                    color="black",
                    linestyle="--",
                    linewidth=2,
                    label=legend,
                )
            else:
                axis.plot(
                    range(len(steps)),
                    series,
                    color=colors[color_index % len(colors)],
                    marker="o",
                    label=legend,
                )
                color_index += 1
        axis.set_title(dimension)
        axis.set_xticks(range(len(steps)), labels, rotation=20, ha="right")
        axis.set_ylim(0, ceiling + 0.3)
        axis.set_xlabel("Logical step")
        axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.38), fontsize=7, frameon=False)
    axes[0].set_ylabel("Remaining uncertainty (bits)")
    figure.tight_layout()
    figure.subplots_adjust(bottom=0.34)
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def _step_labels(steps: Sequence[int]) -> tuple[str, ...]:
    """Return short names for the logical steps."""
    labels = []
    last = steps[-1]
    for index, step in enumerate(steps):
        if step == last:
            labels.append("Vote")
        elif index == 0:
            labels.append("Deal and round 1")
        else:
            labels.append(f"Round {index + 1}")
    return tuple(labels)


_SHORT = {
    "rules": "Rules",
    "D0": "Level 0",
    "D1": "Level 1",
    "D2": "Level 2",
    "S1": "One log",
    "Sk": "Three logs",
    "Sall": "All logs",
    "Sstructured": "Structured file",
}


def _curve_groups(
    points: Sequence[RecoveryPoint],
    dimension: str,
    steps: Sequence[int],
) -> tuple[tuple[tuple[str, ...], tuple[float, ...]], ...]:
    """Return one series for each distinct curve in a dimension."""
    order = [view for view, _label in _view_order(points)]
    buckets: dict[tuple[float, ...], list[str]] = {}
    series_for: dict[str, tuple[float, ...]] = {}
    for view in order:
        series = tuple(
            round(_point_bits(points, dimension, step, view), 6)
            for step in steps
        )
        series_for[view] = series
        buckets.setdefault(series, []).append(view)
    groups = []
    seen: set[tuple[float, ...]] = set()
    for view in order:
        series = series_for[view]
        if series in seen:
            continue
        seen.add(series)
        groups.append((tuple(buckets[series]), series))
    return tuple(groups)


def _group_label(views: Sequence[str]) -> str:
    """Return the legend text for the views on one curve."""
    return ", ".join(_SHORT[view] for view in views)


def _view_order(points: Sequence[RecoveryPoint]) -> tuple[tuple[str, str], ...]:
    """Return rules first, then the saved views that appear."""
    present = {point.view for point in points}
    ordered = [("rules", "Rules")]
    ordered.extend((view, LABELS[view]) for view in LABELS if view in present)
    return tuple(ordered)


def _point_bits(
    points: Sequence[RecoveryPoint],
    dimension: str,
    step: int,
    view: str,
) -> float:
    """Return one stored average."""
    found = [
        point.bits
        for point in points
        if point.dimension == dimension and point.step == step and point.view == view
    ]
    if len(found) != 1:
        raise ValueError("each step must have one average per view")
    return found[0]
