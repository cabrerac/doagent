"""Recover Hidden Profile information curves from each set of files.

The rules supply the true curve.
A view supplies a point only when its files state that point for every deal.
A missing point stays missing.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
import math
from pathlib import Path

from experiments.information_flow.events import (
    ActionEvent,
    BeliefEvent,
    ExecutionEvent,
    MessageDeliveryEvent,
    ObservationEvent,
)
from experiments.information_flow.hidden_profile.access import analyst_logs
from experiments.information_flow.hidden_profile.compare import AGENT_LOGS, ONE_LOG
from experiments.information_flow.hidden_profile.parse import parse_doagent, parse_marble
from experiments.information_flow.hidden_profile.reference import reference_report
from experiments.information_flow.hidden_profile.rules import (
    DEFAULT_CONFIG,
    HiddenProfileConfig,
)
from experiments.information_flow.hidden_profile.run_doagent import run_session
from experiments.information_flow.hidden_profile.run_marble import run_marble
from experiments.information_flow.hidden_profile.score import LABELS
from experiments.information_flow.hidden_profile.service_trace import (
    TRACE_NAME,
    parse_service_trace,
)
from experiments.information_flow.metrics import mutual_information, shannon_entropy

_VIEW_ORDER = tuple(LABELS)


@dataclass(frozen=True)
class CurvePoint:
    """One recovered or true value.

    Args:
        quantity: Name of the information quantity.
        view: Rules or a file view.
        label: Name used on the plot.
        bits: Value in bits.
            None when the files do not state it.
        agent_id: Agent the quantity describes.
        round_index: Disclosure round the quantity describes.
    """

    quantity: str
    view: str
    label: str
    bits: float | None
    agent_id: str | None = None
    round_index: int | None = None


@dataclass(frozen=True)
class CurveReport:
    """Recovered curves and the plot paths.

    Args:
        deals: How many deals were read.
        points: True values and recovered values.
        curves_path: Path of the written table.
        belief_plot: Path of the belief-entropy figure.
        bridge_plot: Path of the holder and delivery figure.
        multi_plot: Path of the multi-information figure.
    """

    deals: int
    points: tuple[CurvePoint, ...]
    curves_path: Path
    belief_plot: Path
    bridge_plot: Path
    multi_plot: Path


def recover_curves(
    output_base: str | Path,
    config: HiddenProfileConfig = DEFAULT_CONFIG,
) -> CurveReport:
    """Recover the curves and write the figures.

    Args:
        output_base: Directory that receives the figures, the table, and the runs.
        config: Hidden profile configuration.

    Returns:
        The true values, the recovered values, and the figure paths.
    """
    folder = Path(output_base)
    folder.mkdir(parents=True, exist_ok=True)
    report = reference_report(config)
    by_deal = [
        _read_deal(index, deal.allocation, deal.count, folder, config, report.bridge_fact_id)
        for index, deal in enumerate(report.deals)
    ]
    points = _points(report, by_deal, config)
    curves_path = folder / "curves.json"
    belief_plot = folder / "belief_entropy.png"
    bridge_plot = folder / "bridge_quantities.png"
    multi_plot = folder / "hold_multi_information.png"
    _write_table(curves_path, len(report.deals), points)
    _write_belief_plot(belief_plot, points, config)
    _write_bridge_plot(bridge_plot, points)
    _write_multi_plot(multi_plot, points, config)
    return CurveReport(
        deals=len(report.deals),
        points=points,
        curves_path=curves_path,
        belief_plot=belief_plot,
        bridge_plot=bridge_plot,
        multi_plot=multi_plot,
    )


def _read_deal(
    index: int,
    allocation: tuple[tuple[str, tuple[str, ...]], ...],
    count: int,
    folder: Path,
    config: HiddenProfileConfig,
    bridge_fact_id: str,
) -> dict[str, object]:
    """Play one deal and read the quantities each view states."""
    assigned = dict(allocation)
    deal_folder = folder / f"deal-{index}"
    sessions = {
        name: run_session(index, level, deal_folder / name, config, assigned)
        for level, name in ((0, "D0"), (1, "D1"), (2, "D2"))
    }
    run_marble(index, deal_folder / "marble", allocation=assigned)
    log_dir = deal_folder / "marble" / "logs"
    parsed = {
        "D0": parse_doagent(sessions["D0"].records_path),
        "D1": parse_doagent(sessions["D1"].records_path),
        "D2": parse_doagent(sessions["D2"].records_path),
        "S1": parse_marble(log_dir, analyst_logs(log_dir, "S1", ONE_LOG)),
        "Sk": parse_marble(log_dir, analyst_logs(log_dir, "Sk", AGENT_LOGS)),
        "Sall": parse_marble(log_dir, analyst_logs(log_dir, "Sall")),
        "Sstructured": parse_service_trace(log_dir / TRACE_NAME),
    }
    return {
        "count": count,
        "views": {
            name: _stated(events, config, bridge_fact_id)
            for name, events in parsed.items()
        },
    }


def _stated(
    events: Sequence[ExecutionEvent],
    config: HiddenProfileConfig,
    bridge_fact_id: str,
) -> dict[str, object]:
    """Return the fields one view states for one deal."""
    beliefs = {
        (agent_id, round_index): _belief(events, agent_id, round_index)
        for round_index in range(config.horizon)
        for agent_id in config.agents
    }
    if not _roster_complete(events, config.agents):
        return {
            "beliefs": beliefs,
            "holder": None,
            "recipient": None,
            "held": {round_index: None for round_index in range(config.horizon)},
        }
    opening = _opening(events, config.agents)
    holder = _one_holder(opening, bridge_fact_id)
    recipient = _one_recipient(events, bridge_fact_id)
    held = {
        round_index: _held(opening, events, config.agents, round_index)
        for round_index in range(config.horizon)
    }
    return {
        "beliefs": beliefs,
        "holder": holder,
        "recipient": recipient,
        "held": held,
    }


def _belief(
    events: Sequence[ExecutionEvent],
    agent_id: str,
    round_index: int,
) -> tuple[float, ...] | None:
    """Return one reported belief when the file states exactly one."""
    matches = [
        event.probabilities
        for event in events
        if isinstance(event, BeliefEvent)
        and event.agent_id == agent_id
        and event.logical_step == round_index
        and event.event_id == f"belief-{round_index}-{agent_id}"
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def _roster_complete(events: Sequence[ExecutionEvent], agents: Sequence[str]) -> bool:
    """Return whether the file states every opening hand and every vote."""
    dealt = {
        event.agent_id
        for event in events
        if isinstance(event, ObservationEvent) and event.channel_id == "deal"
    }
    voters = {
        event.agent_id
        for event in events
        if isinstance(event, ActionEvent) and event.event_id.startswith("vote-")
    }
    return set(agents) <= dealt and set(agents) <= voters


def _opening(
    events: Sequence[ExecutionEvent],
    agents: Sequence[str],
) -> dict[str, set[str]]:
    """Return the fact ids in each opening hand."""
    hands = {
        event.agent_id: {fact_id for fact_id in event.observation.split(",") if fact_id}
        for event in events
        if isinstance(event, ObservationEvent) and event.channel_id == "deal"
    }
    return {agent_id: set(hands[agent_id]) for agent_id in agents}


def _one_holder(opening: Mapping[str, set[str]], fact_id: str) -> str | None:
    """Return the agent dealt one fact when exactly one hand contains it."""
    holders = [agent_id for agent_id, facts in opening.items() if fact_id in facts]
    if len(holders) != 1:
        return None
    return holders[0]


def _one_recipient(events: Sequence[ExecutionEvent], fact_id: str) -> str | None:
    """Return the agent who receives one fact when the file states one delivery."""
    recipients = [
        recipient_id
        for event in events
        if isinstance(event, MessageDeliveryEvent) and event.message == fact_id
        for recipient_id in event.recipient_ids
    ]
    if len(recipients) != 1:
        return None
    return recipients[0]


def _held(
    opening: Mapping[str, set[str]],
    events: Sequence[ExecutionEvent],
    agents: Sequence[str],
    round_index: int,
) -> dict[str, set[str]]:
    """Return who holds each fact after one disclosure round."""
    hands = {agent_id: set(facts) for agent_id, facts in opening.items()}
    for event in events:
        if not isinstance(event, MessageDeliveryEvent):
            continue
        if event.logical_step > round_index:
            continue
        for agent_id in event.recipient_ids:
            if agent_id in hands:
                hands[agent_id].add(event.message)
    return {agent_id: hands[agent_id] for agent_id in agents}


def _points(
    report,
    by_deal: Sequence[Mapping[str, object]],
    config: HiddenProfileConfig,
) -> tuple[CurvePoint, ...]:
    """Return the true curve and each recovered curve."""
    rows = []
    rows.extend(_belief_points(report, by_deal, config))
    rows.extend(_holder_points(report, by_deal, config))
    rows.extend(_delivery_points(report, by_deal, config))
    rows.extend(_multi_points(report, by_deal, config))
    return tuple(rows)


def _belief_points(report, by_deal, config: HiddenProfileConfig) -> list[CurvePoint]:
    """Return belief entropy for the rules and for each view."""
    rows = []
    for round_index in range(config.horizon):
        for agent_id in config.agents:
            truth = _reference_belief(report, agent_id, round_index)
            rows.append(_point("belief_entropy", "rules", "Rules", truth, agent_id, round_index))
            for name in _VIEW_ORDER:
                rows.append(
                    _point(
                        "belief_entropy",
                        name,
                        LABELS[name],
                        _mean_entropy(by_deal, name, agent_id, round_index),
                        agent_id,
                        round_index,
                    )
                )
    return rows


def _holder_points(report, by_deal, config: HiddenProfileConfig) -> list[CurvePoint]:
    """Return the entropy of who is dealt the bridge fact."""
    rows = [
        _point("bridge_holder_entropy", "rules", "Rules", report.bridge_holder_entropy)
    ]
    for name in _VIEW_ORDER:
        rows.append(
            _point(
                "bridge_holder_entropy",
                name,
                LABELS[name],
                _label_entropy(by_deal, name, "holder", config.agents),
            )
        )
    return rows


def _delivery_points(report, by_deal, config: HiddenProfileConfig) -> list[CurvePoint]:
    """Return mutual information between the bridge holder and its recipient."""
    rows = [
        _point(
            "bridge_delivery_mutual_information",
            "rules",
            "Rules",
            report.bridge_delivery_mutual_information,
        )
    ]
    for name in _VIEW_ORDER:
        rows.append(
            _point(
                "bridge_delivery_mutual_information",
                name,
                LABELS[name],
                _delivery_information(by_deal, name, config.agents),
            )
        )
    return rows


def _multi_points(report, by_deal, config: HiddenProfileConfig) -> list[CurvePoint]:
    """Return multi-information of who holds the bridge fact."""
    truth = dict(report.bridge_hold_multi_information)
    rows = []
    for round_index in range(config.horizon):
        rows.append(
            _point(
                "bridge_hold_multi_information",
                "rules",
                "Rules",
                truth[round_index],
                round_index=round_index,
            )
        )
        for name in _VIEW_ORDER:
            rows.append(
                _point(
                    "bridge_hold_multi_information",
                    name,
                    LABELS[name],
                    _multi_information(
                        by_deal,
                        name,
                        config.agents,
                        round_index,
                        report.bridge_fact_id,
                    ),
                    round_index=round_index,
                )
            )
    return rows


def _reference_belief(report, agent_id: str, round_index: int) -> float:
    """Return the true belief entropy for one agent and round."""
    matches = [
        item.value
        for item in report.belief_entropy
        if item.agent_id == agent_id and item.round_index == round_index
    ]
    if len(matches) != 1:
        raise ValueError("the reference must state one belief entropy")
    return matches[0]


def _mean_entropy(
    by_deal: Sequence[Mapping[str, object]],
    view: str,
    agent_id: str,
    round_index: int,
) -> float | None:
    """Return the average entropy of one reported belief."""
    weighted = []
    total = 0
    for deal in by_deal:
        count = int(deal["count"])
        stated = deal["views"][view]
        probabilities = stated["beliefs"][(agent_id, round_index)]
        if probabilities is None:
            return None
        weighted.append(count * shannon_entropy(probabilities))
        total += count
    return math.fsum(weighted) / total


def _label_entropy(
    by_deal: Sequence[Mapping[str, object]],
    view: str,
    field: str,
    labels: Sequence[str],
) -> float | None:
    """Return the entropy of one label across deals."""
    counts: Counter[str] = Counter()
    total = 0
    for deal in by_deal:
        count = int(deal["count"])
        label = deal["views"][view][field]
        if not isinstance(label, str):
            return None
        counts[label] += count
        total += count
    return shannon_entropy(_distribution(counts, labels, total))


def _delivery_information(
    by_deal: Sequence[Mapping[str, object]],
    view: str,
    agents: Sequence[str],
) -> float | None:
    """Return mutual information of the holder and the recipient."""
    counts: Counter[tuple[str, str]] = Counter()
    total = 0
    for deal in by_deal:
        count = int(deal["count"])
        stated = deal["views"][view]
        holder = stated["holder"]
        recipient = stated["recipient"]
        if not isinstance(holder, str) or not isinstance(recipient, str):
            return None
        counts[(holder, recipient)] += count
        total += count
    return mutual_information(_pair_matrix(counts, agents, agents, total))


def _multi_information(
    by_deal: Sequence[Mapping[str, object]],
    view: str,
    agents: Sequence[str],
    round_index: int,
    bridge_fact_id: str,
) -> float | None:
    """Return multi-information of who holds the bridge fact."""
    counts: Counter[tuple[str, ...]] = Counter()
    total = 0
    for deal in by_deal:
        count = int(deal["count"])
        held = deal["views"][view]["held"][round_index]
        if not isinstance(held, dict):
            return None
        pattern = []
        for agent_id in agents:
            facts = held.get(agent_id)
            if not isinstance(facts, set):
                return None
            pattern.append("yes" if bridge_fact_id in facts else "no")
        counts[tuple(pattern)] += count
        total += count
    marginals = []
    for index, _agent_id in enumerate(agents):
        yes = sum(count for pattern, count in counts.items() if pattern[index] == "yes")
        marginals.append(shannon_entropy(_two_probabilities(yes, total)))
    labels = [("yes", "no")] * len(agents)
    joint = _distribution(counts, list(_product(labels)), total)
    return math.fsum(marginals) - shannon_entropy(joint)


def _point(
    quantity: str,
    view: str,
    label: str,
    bits: float | None,
    agent_id: str | None = None,
    round_index: int | None = None,
) -> CurvePoint:
    """Return one curve point."""
    return CurvePoint(
        quantity=quantity,
        view=view,
        label=label,
        bits=bits,
        agent_id=agent_id,
        round_index=round_index,
    )


def _distribution(counts: Mapping[object, int], labels: Sequence[object], total: int) -> list[float]:
    """Return label probabilities that sum to one."""
    values = [counts.get(label, 0) / total for label in labels]
    return _restore_total(values)


def _pair_matrix(
    counts: Mapping[tuple[str, str], int],
    rows: Sequence[str],
    columns: Sequence[str],
    total: int,
) -> list[list[float]]:
    """Return a joint matrix that sums to one."""
    matrix = [
        [counts.get((row, column), 0) / total for column in columns]
        for row in rows
    ]
    flat = _restore_total([value for row in matrix for value in row])
    width = len(columns)
    return [flat[start:start + width] for start in range(0, len(flat), width)]


def _two_probabilities(yes_count: int, total: int) -> list[float]:
    """Return a two-outcome distribution."""
    return _restore_total([yes_count / total, (total - yes_count) / total])


def _restore_total(values: list[float]) -> list[float]:
    """Adjust the largest entry so the values sum to one."""
    residual = 1.0 - math.fsum(values)
    if residual != 0.0:
        index = max(range(len(values)), key=values.__getitem__)
        values[index] += residual
    return values


def _product(factors: Sequence[Sequence[str]]) -> tuple[tuple[str, ...], ...]:
    """Return the cartesian product of string factors."""
    rows: list[tuple[str, ...]] = [()]
    for factor in factors:
        rows = [row + (item,) for row in rows for item in factor]
    return tuple(rows)


def _write_table(path: Path, deals: int, points: Sequence[CurvePoint]) -> None:
    """Write the curve table.

    Args:
        path: Destination of the table.
        deals: How many deals were read.
        points: True values and recovered values.
    """
    payload = {
        "deals": deals,
        "population": "all enumerated deals",
        "points": [
            {
                "quantity": point.quantity,
                "view": point.view,
                "label": point.label,
                "agent_id": point.agent_id,
                "round_index": point.round_index,
                "bits": point.bits,
            }
            for point in points
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_belief_plot(
    path: Path,
    points: Sequence[CurvePoint],
    config: HiddenProfileConfig,
) -> None:
    """Save belief entropy against the disclosure round.

    Args:
        path: Destination of the figure.
        points: True values and recovered values.
        config: Hidden profile configuration.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, len(config.agents), figsize=(11, 4), sharey=True)
    rounds = list(range(config.horizon))
    for axis, agent_id in zip(axes, config.agents):
        for view, style in _styles():
            series = [
                _lookup(points, "belief_entropy", view, agent_id, round_index)
                for round_index in rounds
            ]
            if any(value is None for value in series):
                continue
            axis.plot(rounds, series, label=_caption(view), **style)
        axis.set_title(agent_id)
        axis.set_xlabel("Disclosure round")
        axis.set_xticks(rounds)
        axis.set_ylim(0, 1.6)
    axes[0].set_ylabel("Belief entropy (bits)")
    _finish(figure, axes[0], points, "belief_entropy")
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def _write_bridge_plot(path: Path, points: Sequence[CurvePoint]) -> None:
    """Save holder entropy and delivery mutual information.

    Args:
        path: Destination of the figure.
        points: True values and recovered values.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    quantities = (
        ("bridge_holder_entropy", "Who is dealt the bridge fact"),
        ("bridge_delivery_mutual_information", "Holder and recipient"),
    )
    figure, axes = plt.subplots(1, 2, figsize=(10, 4))
    for axis, (quantity, title) in zip(axes, quantities):
        labels = []
        values = []
        for view, _style in _styles():
            value = _lookup(points, quantity, view, None, None)
            if value is None:
                continue
            labels.append(_caption(view))
            values.append(value)
        axis.bar(range(len(values)), values)
        axis.set_xticks(range(len(labels)), labels, rotation=30, ha="right")
        axis.set_title(title)
        axis.set_ylabel("Bits")
    _finish(figure, axes[0], points, "bridge_holder_entropy")
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def _write_multi_plot(
    path: Path,
    points: Sequence[CurvePoint],
    config: HiddenProfileConfig,
) -> None:
    """Save multi-information of who holds the bridge fact.

    Args:
        path: Destination of the figure.
        points: True values and recovered values.
        config: Hidden profile configuration.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(7, 4))
    rounds = list(range(config.horizon))
    for view, style in _styles():
        series = [
            _lookup(points, "bridge_hold_multi_information", view, None, round_index)
            for round_index in rounds
        ]
        if any(value is None for value in series):
            continue
        axis.plot(rounds, series, label=_caption(view), **style)
    axis.set_xlabel("Disclosure round")
    axis.set_ylabel("Multi-information (bits)")
    axis.set_xticks(rounds)
    axis.set_ylim(0, 2)
    _finish(figure, axis, points, "bridge_hold_multi_information")
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)


def _styles() -> tuple[tuple[str, dict[str, object]], ...]:
    """Return a drawing style for the rules and each file view."""
    return (
        ("rules", {"color": "black", "linewidth": 2, "marker": "o"}),
        ("D0", {"color": "#4C78A8", "linestyle": "none", "marker": "o"}),
        ("D1", {"color": "#F58518", "linestyle": "none", "marker": "s"}),
        ("D2", {"color": "#54A24B", "linestyle": "none", "marker": "^"}),
        ("S1", {"color": "#E45756", "linestyle": "--", "marker": "v"}),
        ("Sk", {"color": "#72B7B2", "linestyle": "--", "marker": "D"}),
        ("Sall", {"color": "#B279A2", "linestyle": "--", "marker": "P"}),
        ("Sstructured", {"color": "#FF9DA6", "linestyle": ":", "marker": "X"}),
    )


def _caption(view: str) -> str:
    """Return the plot name of one view."""
    if view == "rules":
        return "Rules"
    return LABELS[view]


def _lookup(
    points: Sequence[CurvePoint],
    quantity: str,
    view: str,
    agent_id: str | None,
    round_index: int | None,
) -> float | None:
    """Return one stored value."""
    matches = [
        point.bits
        for point in points
        if point.quantity == quantity
        and point.view == view
        and point.agent_id == agent_id
        and point.round_index == round_index
    ]
    if len(matches) != 1:
        raise ValueError("the curve must state one value")
    return matches[0]


def _finish(figure, axis, points: Sequence[CurvePoint], quantity: str) -> None:
    """Add the legend and name the views that do not state the quantity."""
    missing = []
    for view in _VIEW_ORDER:
        stated = [
            point.bits
            for point in points
            if point.quantity == quantity and point.view == view
        ]
        if stated and all(value is None for value in stated):
            missing.append(LABELS[view])
    if missing:
        figure.suptitle("Not stated: " + ", ".join(missing), fontsize=9)
    figure.tight_layout(rect=(0, 0.18, 1, 0.92))
    handles, labels = axis.get_legend_handles_labels()
    if handles:
        figure.legend(handles, labels, loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.01))
