"""Plot Hidden Profile results by dimension and by question type.

Record questions are answered from the record in front of you.
Link questions follow a declared link.
A question the rules leave unstated is shown apart from the match rate.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path

from experiments.information_flow.events import ExecutionEvent
from experiments.information_flow.hidden_profile.access import analyst_logs
from experiments.information_flow.hidden_profile.compare import (
    AGENT_LOGS,
    ONE_LOG,
    _bridge_message_id,
)
from experiments.information_flow.hidden_profile.parse import parse_doagent, parse_marble
from experiments.information_flow.hidden_profile.reference import reference_report
from experiments.information_flow.hidden_profile.rules import (
    DEFAULT_CONFIG,
    HiddenProfileConfig,
    run_episode,
)
from experiments.information_flow.hidden_profile.score import LABELS
from experiments.information_flow.hidden_profile.service_trace import (
    TRACE_NAME,
    parse_service_trace,
)
from experiments.information_flow.queries import Answer, decode

_VIEWS = tuple(LABELS)
_DIMENSIONS = ("Accountability", "Traceability", "Explainability")


@dataclass(frozen=True)
class AskedQuestion:
    """One question asked of every deal.

    Args:
        dimension: Accountability, traceability, or explainability.
        kind: Record or link.
        label: Question in ordinary language.
        answer: Reads one event list.
    """

    dimension: str
    kind: str
    label: str
    answer: Callable[[Sequence[ExecutionEvent]], Answer]


@dataclass(frozen=True)
class QuestionResult:
    """How often one view matched the rules on one question.

    Args:
        dimension: Accountability, traceability, or explainability.
        kind: Record or link.
        label: Question in ordinary language.
        view: Rules or a file view.
        matched: Deals whose stated answer matched the rules.
        stated: Deals where the rules state an answer.
        unstated: Deals where the rules do not state an answer.
    """

    dimension: str
    kind: str
    label: str
    view: str
    matched: int
    stated: int
    unstated: int


@dataclass(frozen=True)
class Breakdown:
    """Match counts and the figure paths.

    Args:
        deals: How many deals were read.
        results: One row per question and view.
        questions_plot: Path of the question figure.
        dimensions_plot: Path of the dimension figure.
        table_path: Path of the written table.
    """

    deals: int
    results: tuple[QuestionResult, ...]
    questions_plot: Path
    dimensions_plot: Path
    table_path: Path


def plot_breakdown(
    output_base: str | Path,
    config: HiddenProfileConfig = DEFAULT_CONFIG,
    deal_indexes: Sequence[int] | None = None,
    logging_levels: Sequence[int] = (0, 1, 2),
) -> Breakdown:
    """Read the saved deals and write the dimension figures.

    The deals must already contain the session files and the MARBLE logs.

    Args:
        output_base: Directory that holds the deal folders and the figures.
        config: Hidden profile configuration.
        deal_indexes: Deals to read.
            Every enumerated deal is read when this is omitted.
        logging_levels: Session levels whose record files are read.

    Returns:
        The match counts and the figure paths.

    Raises:
        ValueError: A saved deal is missing.
    """
    folder = Path(output_base)
    report = reference_report(config)
    indexes = tuple(range(len(report.deals)) if deal_indexes is None else deal_indexes)
    results = _score_saved(folder, report, config, indexes, logging_levels)
    questions_plot = folder / "questions.png"
    dimensions_plot = folder / "dimensions.png"
    table_path = folder / "breakdown.json"
    _write_table(table_path, len(indexes), results)
    _write_questions(questions_plot, results)
    _write_dimensions(dimensions_plot, results)
    return Breakdown(
        deals=len(report.deals),
        results=results,
        questions_plot=questions_plot,
        dimensions_plot=dimensions_plot,
        table_path=table_path,
    )


def _score_saved(
    folder: Path,
    report,
    config: HiddenProfileConfig,
    deal_indexes: Sequence[int],
    logging_levels: Sequence[int],
) -> tuple[QuestionResult, ...]:
    """Score each saved deal against the rules."""
    totals: dict[tuple[str, str, str, str], list[int]] = {}
    for index in deal_indexes:
        deal = report.deals[index]
        rules = run_episode(index, config, dict(deal.allocation)).events
        message_id = _bridge_message_id(rules, report.bridge_fact_id)
        recipient = _recipient(rules, message_id)
        questions = _questions(config, report.bridge_fact_id, message_id, recipient, rules)
        views = _load_views(folder / f"deal-{index}", logging_levels)
        views["rules"] = rules
        for question in questions:
            truth = question.answer(rules)
            for name, events in views.items():
                if name == "rules":
                    continue
                key = (question.dimension, question.kind, question.label, name)
                counts = totals.setdefault(key, [0, 0, 0])
                if truth.kind == "unknown":
                    counts[2] += 1
                    continue
                counts[1] += 1
                if question.answer(events) == truth:
                    counts[0] += 1
    return tuple(
        QuestionResult(dimension, kind, label, view, matched, stated, unstated)
        for (dimension, kind, label, view), (matched, stated, unstated) in totals.items()
    )


def _load_views(
    deal: Path,
    logging_levels: Sequence[int],
) -> dict[str, tuple[ExecutionEvent, ...]]:
    """Return the saved session files and MARBLE logs for one deal."""
    if not deal.is_dir():
        raise ValueError("a saved deal is missing")
    loaded: dict[str, tuple[ExecutionEvent, ...]] = {}
    for level in logging_levels:
        records = deal / f"D{level}" / "records.json"
        if not records.is_file():
            raise ValueError("a saved deal is missing")
        loaded[f"D{level}"] = parse_doagent(records)
    log_dir = deal / "marble" / "logs"
    loaded.update(
        {
            "S1": parse_marble(log_dir, analyst_logs(log_dir, "S1", ONE_LOG)),
            "Sk": parse_marble(log_dir, analyst_logs(log_dir, "Sk", AGENT_LOGS)),
            "Sall": parse_marble(log_dir, analyst_logs(log_dir, "Sall")),
            "Sstructured": parse_service_trace(log_dir / TRACE_NAME),
        }
    )
    return loaded


def _questions(
    config: HiddenProfileConfig,
    bridge_fact_id: str,
    message_id: str,
    recipient: str,
    rules: Sequence[ExecutionEvent],
) -> tuple[AskedQuestion, ...]:
    """Return the questions for one deal, in display order."""
    order_ids = _game_order(rules)
    rows = [
        AskedQuestion(
            "Accountability",
            "record",
            "Who sent the bridge fact?",
            lambda events: decode(events, "sender", event_id=message_id),
        ),
        AskedQuestion(
            "Accountability",
            "record",
            "Who received the bridge fact?",
            lambda events: decode(events, "recipients", event_id=message_id),
        ),
        AskedQuestion(
            "Accountability",
            "record",
            "Who could see the bridge fact at the start?",
            lambda events: decode(
                events,
                "fact_access",
                fact_id=bridge_fact_id,
                logical_step=0,
            ),
        ),
        AskedQuestion(
            "Accountability",
            "record",
            "Who could see the bridge fact after round 1?",
            lambda events: decode(
                events,
                "fact_access",
                fact_id=bridge_fact_id,
                logical_step=1,
            ),
        ),
    ]
    for agent_id in config.agents:
        rows.append(
            AskedQuestion(
                "Accountability",
                "record",
                f"What did {agent_id} vote?",
                lambda events, agent_id=agent_id: decode(
                    events,
                    "decision_action",
                    event_id=f"vote-{agent_id}",
                ),
            )
        )
    rows.append(
        AskedQuestion(
            "Accountability",
            "link",
            "Which votes produced the group choice?",
            lambda events: decode(events, "group_votes", event_id="outcome-group"),
        )
    )
    rows.append(
        AskedQuestion(
            "Traceability",
            "record",
            "In what order did the deals, messages, and votes happen?",
            lambda events: _shared_order(events, order_ids),
        )
    )
    rows.append(
        AskedQuestion(
            "Traceability",
            "record",
            "Which message first brought the bridge fact to its recipient?",
            lambda events: decode(
                events,
                "first_access",
                fact_id=bridge_fact_id,
                agent_id=recipient,
            ),
        )
    )
    rows.append(
        AskedQuestion(
            "Traceability",
            "link",
            "What path did the bridge fact take?",
            lambda events: decode(
                events,
                "fact_path",
                fact_id=bridge_fact_id,
                agent_id=recipient,
            ),
        )
    )
    rows.append(
        AskedQuestion(
            "Traceability",
            "link",
            "Does each vote point at the reported chances?",
            lambda events: _belief_links(events, config.agents),
        )
    )
    rows.append(
        AskedQuestion(
            "Traceability",
            "link",
            "Which update produced the group choice?",
            lambda events: decode(events, "transition_update", event_id="outcome-group"),
        )
    )
    rows.append(
        AskedQuestion(
            "Explainability",
            "record",
            "What chances did agent-a report before the vote?",
            lambda events: _chances(events),
        )
    )
    for agent_id in config.agents:
        rows.append(
            AskedQuestion(
                "Explainability",
                "link",
                f"Why did {agent_id} vote that way?",
                lambda events, agent_id=agent_id: decode(
                    events,
                    "vote_basis",
                    event_id=f"vote-{agent_id}",
                ),
            )
        )
    rows.append(
        AskedQuestion(
            "Explainability",
            "link",
            "How did the recipient's chances change?",
            lambda events: decode(
                events,
                "belief_change",
                event_id=message_id,
                agent_id=recipient,
            ),
        )
    )
    for agent_id in config.agents:
        rows.append(
            AskedQuestion(
                "Explainability",
                "link",
                f"Did {agent_id} vote for the top chance?",
                lambda events, agent_id=agent_id: decode(
                    events,
                    "vote_matches_chances",
                    event_id=f"vote-{agent_id}",
                ),
            )
        )
    return tuple(rows)


def _game_order(events: Sequence[ExecutionEvent]) -> tuple[str, ...]:
    """Return the deal, message, and vote ids in rules order."""
    return tuple(
        event.event_id
        for event in sorted(events, key=lambda event: event.sequence_index)
        if event.event_id.startswith(("deal-", "disclosure-", "vote-"))
    )


def _shared_order(events: Sequence[ExecutionEvent], order_ids: Sequence[str]) -> Answer:
    """Return the shared order when every game event is present."""
    wanted = set(order_ids)
    found = [
        event.event_id
        for event in sorted(events, key=lambda event: event.sequence_index)
        if event.event_id in wanted
    ]
    if found != list(order_ids):
        return Answer("unknown")
    return Answer("exact", tuple(order_ids))


def _belief_links(events: Sequence[ExecutionEvent], agents: Sequence[str]) -> Answer:
    """Return whether every vote points at one belief."""
    for agent_id in agents:
        answer = decode(events, "decision_inputs", event_id=f"vote-{agent_id}")
        if answer.kind != "exact" or not isinstance(answer.value, tuple):
            return Answer("unknown")
        beliefs = [
            item
            for item in answer.value
            if isinstance(item, str) and item.startswith("belief-")
        ]
        if len(beliefs) != 1:
            return Answer("unknown")
    return Answer("exact", "each vote points at one belief")


def _chances(events: Sequence[ExecutionEvent]) -> Answer:
    """Return agent A's chances before the vote."""
    answer = decode(events, "reported_chances", event_id="belief-2-agent-a")
    if answer.kind == "unknown":
        return decode(events, "reported_chances", event_id="belief-vote-agent-a")
    return answer


def _recipient(events: Sequence[ExecutionEvent], message_id: str) -> str:
    """Return the one recipient of the bridge message."""
    answer = decode(events, "recipients", event_id=message_id)
    if answer.kind != "exact" or not isinstance(answer.value, frozenset):
        raise ValueError("the bridge message must name its recipients")
    if len(answer.value) != 1:
        raise ValueError("the bridge message must name one recipient")
    return next(iter(answer.value))


def _write_table(path: Path, deals: int, results: Sequence[QuestionResult]) -> None:
    """Write the match counts.

    Args:
        path: Destination of the table.
        deals: How many deals were read.
        results: Match counts per question and view.
    """
    payload = {
        "deals": deals,
        "results": [
            {
                "dimension": item.dimension,
                "kind": item.kind,
                "label": item.label,
                "view": item.view,
                "matched": item.matched,
                "stated": item.stated,
                "unstated": item.unstated,
            }
            for item in results
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_questions(path: Path, results: Sequence[QuestionResult]) -> None:
    """Save one cell per question and view.

    Args:
        path: Destination of the figure.
        results: Match counts per question and view.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    keys, labels = _question_labels(results)
    views = _present_views(results)
    grid = []
    notes = []
    for label in keys:
        row = []
        note = []
        for view in views:
            item = _find(results, label, view)
            if item.stated == 0:
                row.append(np.nan)
                note.append("n/a")
            else:
                row.append(item.matched / item.stated)
                note.append(f"{item.matched}/{item.stated}")
        grid.append(row)
        notes.append(note)
    figure, axis = plt.subplots(figsize=(12, 12))
    colors = plt.cm.RdYlGn.copy()
    colors.set_bad("#d9d9d9")
    image = axis.imshow(np.array(grid, dtype=float), cmap=colors, vmin=0, vmax=1, aspect="auto")
    axis.set_xticks(range(len(views)), [LABELS[view] for view in views], rotation=30, ha="right")
    axis.set_yticks(range(len(labels)), labels, fontsize=8)
    for row_index, row in enumerate(notes):
        for column_index, text in enumerate(row):
            axis.text(column_index, row_index, text, ha="center", va="center", fontsize=7)
    figure.colorbar(image, ax=axis, fraction=0.03, pad=0.02, label="Share of deals recovered")
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def _write_dimensions(path: Path, results: Sequence[QuestionResult]) -> None:
    """Save record and link match rates for each dimension.

    Args:
        path: Destination of the figure.
        results: Match counts per question and view.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
    views = _present_views(results)
    positions = list(range(len(views)))
    for axis, dimension in zip(axes, _DIMENSIONS):
        for offset, kind, color in ((-0.15, "record", "#4C78A8"), (0.15, "link", "#F58518")):
            shares = [_kind_share(results, dimension, kind, view) for view in views]
            axis.bar(
                [position + offset for position in positions],
                [0 if share is None else share for share in shares],
                width=0.3,
                color=color,
                label=kind.capitalize() + " questions",
            )
        axis.set_title(dimension)
        axis.set_xticks(positions, [LABELS[view] for view in views], rotation=30, ha="right")
        axis.set_ylim(0, 1.05)
    axes[0].set_ylabel("Share of stated questions recovered")
    axes[0].legend(loc="upper left", fontsize=8)
    figure.tight_layout()
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def _present_views(results: Sequence[QuestionResult]) -> tuple[str, ...]:
    """Return the views that have at least one saved row, in plot order."""
    present = {item.view for item in results}
    return tuple(view for view in _VIEWS if view in present)


def _question_labels(results: Sequence[QuestionResult]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return question keys and the labels drawn on the figure."""
    keys = []
    labels = []
    for item in results:
        if item.label in keys:
            continue
        keys.append(item.label)
        labels.append(f"{item.dimension}, {item.kind}: {item.label}")
    return tuple(keys), tuple(labels)


def _find(results: Sequence[QuestionResult], label: str, view: str) -> QuestionResult:
    """Return one question row."""
    matches = [item for item in results if item.label == label and item.view == view]
    if len(matches) != 1:
        raise ValueError("each question must have one row per view")
    return matches[0]


def _kind_share(
    results: Sequence[QuestionResult],
    dimension: str,
    kind: str,
    view: str,
) -> float | None:
    """Return the match share for one dimension, type, and view."""
    chosen = [
        item
        for item in results
        if item.dimension == dimension and item.kind == kind and item.view == view and item.stated
    ]
    stated = sum(item.stated for item in chosen)
    if stated == 0:
        return None
    matched = sum(item.matched for item in chosen)
    return matched / stated
