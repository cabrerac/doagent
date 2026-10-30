"""Ask the recorded questions of every Hidden Profile deal.

Each view also says what each vote was based on.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from experiments.information_flow.events import ExecutionEvent, MessageDeliveryEvent
from experiments.information_flow.hidden_profile.access import COMPONENT_LOGS, analyst_logs
from experiments.information_flow.hidden_profile.parse import (
    parse_doagent,
    parse_marble,
    vote_bases,
)
from experiments.information_flow.hidden_profile.reading import (
    ReadingCost,
    log_reading,
    session_reading,
)
from experiments.information_flow.hidden_profile.reference import reference_report
from experiments.information_flow.hidden_profile.rules import (
    DEFAULT_CONFIG,
    HiddenProfileConfig,
    run_episode,
)
from experiments.information_flow.hidden_profile.run_doagent import run_session
from experiments.information_flow.hidden_profile.run_marble import run_marble
from experiments.information_flow.hidden_profile.service_trace import (
    TRACE_NAME,
    parse_service_trace,
    trace_reading,
)
from experiments.information_flow.queries import Answer, decode

AGENT_LOGS = tuple(
    name for name in COMPONENT_LOGS if name.startswith("HiddenProfileAgent.")
)
ONE_LOG = "HiddenProfileAgent.agent-c.log"


@dataclass(frozen=True)
class ViewAnswers:
    """Answers one artifact view gave for one deal.

    Args:
        source: Name of the artifact view.
        recipients: Who received the bridge disclosure.
        access_before: Who could access the bridge fact after round 0.
        access_after: Who could access the bridge fact after round 1.
        votes: Actor and action for each vote, in agent order.
        bases: Chances and fact names behind each vote, in agent order.
            Unknown when the artifact does not state them.
        sender: Who sent the bridge disclosure.
        group_votes: Votes named as producing the group choice.
        bridge_path: Events that brought the bridge fact to its recipient.
        chances: Chances reported for agent A before the vote.
        belief_change: Chances for the bridge recipient before and after that message.
        vote_match: Whether each vote picked the route ranked first.
        transition: Recorded update for the group outcome.
        reading: Files, bytes, and joins used to build this view.
            The rules view has none.
    """

    source: str
    recipients: Answer
    access_before: Answer
    access_after: Answer
    votes: tuple[Answer, ...]
    bases: tuple[Answer, ...]
    sender: Answer
    group_votes: Answer
    bridge_path: Answer
    chances: Answer
    belief_change: Answer
    vote_match: tuple[Answer, ...]
    transition: Answer
    reading: ReadingCost | None = None


@dataclass(frozen=True)
class DealComparison:
    """Answers for one deal from the rules and from each artifact view.

    Args:
        index: Position of the deal in the reference list.
        views: Rules answers, then each artifact view.
    """

    index: int
    views: tuple[ViewAnswers, ...]


def compare_deals(
    output_base: str | Path,
    config: HiddenProfileConfig = DEFAULT_CONFIG,
) -> tuple[DealComparison, ...]:
    """Play every enumerated deal and record the frozen answers.

    Args:
        output_base: Directory that receives comparison.json and the run files.
        config: Hidden profile configuration.

    Returns:
        One comparison per deal, in reference order.
    """
    folder = Path(output_base)
    folder.mkdir(parents=True, exist_ok=True)
    report = reference_report(config)
    comparisons = tuple(
        _compare_one(index, dict(deal.allocation), folder, config, report.bridge_fact_id)
        for index, deal in enumerate(report.deals)
    )
    payload = {
        "bridge_fact_id": report.bridge_fact_id,
        "deals": [_deal_payload(comparison) for comparison in comparisons],
    }
    (folder / "comparison.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return comparisons


def _compare_one(
    index: int,
    allocation: Mapping[str, Sequence[str]],
    folder: Path,
    config: HiddenProfileConfig,
    bridge_fact_id: str,
) -> DealComparison:
    """Play one deal through the rules, DOAgent, and the MARBLE views."""
    rules_events = run_episode(index, config, allocation).events
    message_id = _bridge_message_id(rules_events, bridge_fact_id)
    deal_folder = folder / f"deal-{index}"
    session = run_session(
        index,
        output_base=deal_folder / "doagent",
        config=config,
        allocation=allocation,
    )
    run_marble(
        index,
        deal_folder / "marble",
        allocation=allocation,
    )
    log_dir = deal_folder / "marble" / "logs"
    sall_logs = analyst_logs(log_dir, "Sall")
    agent_logs = analyst_logs(log_dir, "Sk", AGENT_LOGS)
    one_log = analyst_logs(log_dir, "S1", ONE_LOG)
    views = (
        _view("rules", rules_events, message_id, bridge_fact_id, config),
        _view(
            "doagent",
            parse_doagent(session.records_path),
            message_id,
            bridge_fact_id,
            config,
            session_reading(session.records_path),
        ),
        _view(
            "marble_sall",
            parse_marble(log_dir, sall_logs),
            message_id,
            bridge_fact_id,
            config,
            log_reading(sall_logs),
        ),
        _view(
            "marble_agents",
            parse_marble(log_dir, agent_logs),
            message_id,
            bridge_fact_id,
            config,
            log_reading(agent_logs),
        ),
        _view(
            "marble_one",
            parse_marble(log_dir, one_log),
            message_id,
            bridge_fact_id,
            config,
            log_reading(one_log),
        ),
        _view(
            "marble_structured",
            parse_service_trace(log_dir / TRACE_NAME),
            message_id,
            bridge_fact_id,
            config,
            trace_reading(log_dir / TRACE_NAME),
        ),
    )
    return DealComparison(index=index, views=views)


def _view(
    source: str,
    events: Sequence[ExecutionEvent],
    message_id: str,
    bridge_fact_id: str,
    config: HiddenProfileConfig,
    reading: ReadingCost | None = None,
) -> ViewAnswers:
    """Ask the frozen questions of one event list."""
    recipients = decode(events, "recipients", event_id=message_id)
    recipient_id = _one_recipient(recipients)
    chances = decode(events, "reported_chances", event_id="belief-2-agent-a")
    if chances.kind == "unknown":
        chances = decode(events, "reported_chances", event_id="belief-vote-agent-a")
    change = Answer("unknown")
    path = Answer("unknown")
    if recipient_id is not None:
        change = decode(
            events,
            "belief_change",
            event_id=message_id,
            agent_id=recipient_id,
        )
        path = decode(
            events,
            "fact_path",
            fact_id=bridge_fact_id,
            agent_id=recipient_id,
        )
    return ViewAnswers(
        source=source,
        recipients=recipients,
        access_before=decode(events, "fact_access", fact_id=bridge_fact_id, logical_step=0),
        access_after=decode(events, "fact_access", fact_id=bridge_fact_id, logical_step=1),
        votes=tuple(
            decode(events, "decision_action", event_id=f"vote-{agent_id}")
            for agent_id in config.agents
        ),
        bases=vote_bases(events, config.agents),
        sender=decode(events, "sender", event_id=message_id),
        group_votes=decode(events, "group_votes", event_id="outcome-group"),
        bridge_path=path,
        chances=chances,
        belief_change=change,
        vote_match=tuple(
            decode(events, "vote_matches_chances", event_id=f"vote-{agent_id}")
            for agent_id in config.agents
        ),
        transition=decode(events, "transition_update", event_id="outcome-group"),
        reading=reading,
    )


def _one_recipient(answer: Answer) -> str | None:
    """Return the recipient when a message names exactly one."""
    if answer.kind != "exact" or not isinstance(answer.value, frozenset):
        return None
    if len(answer.value) != 1:
        return None
    return next(iter(answer.value))


def _bridge_message_id(events: Sequence[ExecutionEvent], bridge_fact_id: str) -> str:
    """Return the disclosure that carries the bridge fact."""
    found = [
        event.event_id
        for event in events
        if isinstance(event, MessageDeliveryEvent) and event.message == bridge_fact_id
    ]
    if len(found) != 1:
        raise ValueError("the deal must disclose the bridge fact once")
    return found[0]


def _deal_payload(comparison: DealComparison) -> dict[str, object]:
    """Return one deal as JSON-ready fields."""
    return {
        "index": comparison.index,
        "views": [_view_payload(view) for view in comparison.views],
    }


def _view_payload(view: ViewAnswers) -> dict[str, object]:
    """Return one view as JSON-ready fields."""
    return {
        "source": view.source,
        "recipients": _answer_payload(view.recipients),
        "access_before": _answer_payload(view.access_before),
        "access_after": _answer_payload(view.access_after),
        "votes": [_answer_payload(answer) for answer in view.votes],
        "bases": [_answer_payload(answer) for answer in view.bases],
        "sender": _answer_payload(view.sender),
        "group_votes": _answer_payload(view.group_votes),
        "bridge_path": _answer_payload(view.bridge_path),
        "chances": _answer_payload(view.chances),
        "belief_change": _answer_payload(view.belief_change),
        "vote_match": [_answer_payload(answer) for answer in view.vote_match],
        "transition": _answer_payload(view.transition),
        "reading": _reading_payload(view.reading),
    }


def _reading_payload(reading: ReadingCost | None) -> dict[str, int] | None:
    """Return one reading cost as JSON-ready fields."""
    if reading is None:
        return None
    return {
        "files_opened": reading.files_opened,
        "bytes_read": reading.bytes_read,
        "joins": reading.joins,
    }


def _answer_payload(answer: Answer) -> dict[str, object]:
    """Return one answer as JSON-ready fields."""
    return {
        "kind": answer.kind,
        "value": _jsonable(answer.value),
        "candidates": _jsonable(answer.candidates),
    }


def _jsonable(value: object) -> object:
    """Return a JSON-ready copy of an answer value."""
    if isinstance(value, frozenset):
        return sorted(value)
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    return value
