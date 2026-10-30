"""Answer a fixed question list from neutral execution events."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from experiments.information_flow.events import (
    ActionEvent,
    BeliefEvent,
    ExecutionEvent,
    MessageDeliveryEvent,
    ObservationEvent,
    OutcomeEvent,
    TransitionEvent,
)


@dataclass(frozen=True)
class Query:
    """Name one frozen analyst question.

    Args:
        id: Stable question identifier.
        question: The question in ordinary language.
    """

    id: str
    question: str


QUERIES: tuple[Query, ...] = (
    Query("sender", "Who sent this message?"),
    Query("recipients", "Who received this message?"),
    Query("fact_access", "Who could see this fact by this round?"),
    Query("decision_action", "Who acted, and what did they choose?"),
    Query("group_votes", "Which votes produced the group choice?"),
    Query("event_order", "In what order did these events happen?"),
    Query("first_access", "Which message first delivered this fact to this player?"),
    Query(
        "decision_observation",
        "What was the player looking at when they decided?",
    ),
    Query("decision_inputs", "Which earlier records does this decision point at?"),
    Query("fact_path", "What path did this fact take from its source to this player?"),
    Query("transition_update", "Which update produced this result?"),
    Query("reported_chances", "What chances did this player report?"),
    Query("vote_basis", "Why did this player vote this way?"),
    Query("belief_change", "How did the chances change after this message?"),
    Query(
        "vote_matches_chances",
        "Did this vote pick the route the chances ranked first?",
    ),
)


@dataclass(frozen=True)
class Answer:
    """Hold one exact value, an unknown, or a candidate set.

    Args:
        kind: exact, unknown, or candidates.
        value: The single answer when kind is exact.
        candidates: The possible answers when kind is candidates.

    Raises:
        ValueError: The kind and the stored answer do not match.
    """

    kind: str
    value: object = None
    candidates: tuple[object, ...] | None = None

    def __post_init__(self) -> None:
        """Reject an answer that mixes the three kinds."""
        if self.kind == "exact":
            if self.value is None or self.candidates is not None:
                raise ValueError("an exact answer stores one value")
            return
        if self.kind == "unknown":
            if self.value is not None or self.candidates is not None:
                raise ValueError("an unknown answer stores nothing")
            return
        if self.kind != "candidates" or not isinstance(self.candidates, tuple):
            raise ValueError("kind must be exact, unknown, or candidates")
        if self.value is not None or len(self.candidates) < 2:
            raise ValueError("candidates stores at least two values")
        if len(set(self.candidates)) != len(self.candidates):
            raise ValueError("candidates must be unique")


def decode(
    events: Sequence[ExecutionEvent],
    query_id: str,
    *,
    event_id: str | None = None,
    fact_id: str | None = None,
    agent_id: str | None = None,
    logical_step: int | None = None,
    event_ids: Sequence[str] | None = None,
) -> Answer:
    """Answer one frozen question from neutral events.

    Args:
        events: Ordered execution events.
            Private truth is not read.
        query_id: Identifier from the frozen question list.
        event_id: Event named by the question.
        fact_id: Fact named by an access question.
        agent_id: Agent named by a first-access question.
        logical_step: Inclusive model time for a fact-access question.
        event_ids: Events whose order is requested.
            Omit this to order every event.

    Returns:
        An exact answer, unknown, or a candidate set.

    Raises:
        ValueError: The question or a required name is missing.
    """
    known = {query.id for query in QUERIES}
    if query_id not in known:
        raise ValueError("query_id must name a frozen question")
    ordered = tuple(sorted(events, key=lambda event: event.sequence_index))
    if query_id == "sender":
        return _sender(ordered, _required(event_id, "event_id"))
    if query_id == "recipients":
        return _recipients(ordered, _required(event_id, "event_id"))
    if query_id == "fact_access":
        return _fact_access(
            ordered,
            _required(fact_id, "fact_id"),
            _required_step(logical_step),
        )
    if query_id == "first_access":
        return _first_access(
            ordered,
            _required(fact_id, "fact_id"),
            _required(agent_id, "agent_id"),
        )
    if query_id == "decision_observation":
        return _decision_observation(ordered, _required(event_id, "event_id"))
    if query_id == "decision_action":
        return _decision_action(ordered, _required(event_id, "event_id"))
    if query_id == "group_votes":
        return _group_votes(ordered, _required(event_id, "event_id"))
    if query_id == "fact_path":
        return _fact_path(
            ordered,
            _required(fact_id, "fact_id"),
            _required(agent_id, "agent_id"),
        )
    if query_id == "transition_update":
        return _transition_update(ordered, _required(event_id, "event_id"))
    if query_id == "decision_inputs":
        return _decision_inputs(ordered, _required(event_id, "event_id"))
    if query_id == "reported_chances":
        return _reported_chances(ordered, _required(event_id, "event_id"))
    if query_id == "vote_basis":
        return _vote_basis(ordered, _required(event_id, "event_id"))
    if query_id == "belief_change":
        return _belief_change(
            ordered,
            _required(event_id, "event_id"),
            _required(agent_id, "agent_id"),
        )
    if query_id == "vote_matches_chances":
        return _vote_matches_chances(ordered, _required(event_id, "event_id"))
    return _event_order(ordered, event_ids)


def _sender(events: tuple[ExecutionEvent, ...], event_id: str) -> Answer:
    """Return the agent who sent one message."""
    event = _find(events, event_id)
    if not isinstance(event, MessageDeliveryEvent):
        return Answer("unknown")
    return Answer("exact", event.sender_id)


def _recipients(events: tuple[ExecutionEvent, ...], event_id: str) -> Answer:
    """Return the agents who received one message."""
    event = _find(events, event_id)
    if not isinstance(event, MessageDeliveryEvent):
        return Answer("unknown")
    return Answer("exact", frozenset(event.recipient_ids))


def _fact_access(
    events: tuple[ExecutionEvent, ...],
    fact_id: str,
    logical_step: int,
) -> Answer:
    """Return agents who could access one fact at or before a model time.

    A missing deal observation makes the holder set unknown.
    """
    if not any(isinstance(event, ObservationEvent) for event in events):
        return Answer("unknown")
    holders: set[str] = set()
    for event in events:
        if event.logical_step > logical_step:
            continue
        holders.update(_granted(event, fact_id))
    return Answer("exact", frozenset(holders))


def _first_access(
    events: tuple[ExecutionEvent, ...],
    fact_id: str,
    agent_id: str,
) -> Answer:
    """Return the earliest event that gave one agent a fact."""
    found = [
        event
        for event in events
        if agent_id in _granted(event, fact_id)
    ]
    if not found:
        return Answer("unknown")
    earliest = min(found, key=lambda event: event.sequence_index)
    return Answer("exact", earliest.event_id)


def _decision_observation(events: tuple[ExecutionEvent, ...], event_id: str) -> Answer:
    """Return observations reached by following declared inputs."""
    if _find(events, event_id) is None:
        return Answer("unknown")
    observations = [
        event.observation
        for event in _reachable(events, event_id)
        if isinstance(event, ObservationEvent)
    ]
    if not observations:
        return Answer("unknown")
    if len(observations) == 1:
        return Answer("exact", observations[0])
    return Answer("exact", tuple(observations))


def _group_votes(events: tuple[ExecutionEvent, ...], event_id: str) -> Answer:
    """Return the votes named as producing one group result."""
    event = _find(events, event_id)
    if not isinstance(event, OutcomeEvent) or not event.contributing_event_ids:
        return Answer("unknown")
    return Answer("exact", event.contributing_event_ids)


def _fact_path(
    events: tuple[ExecutionEvent, ...],
    fact_id: str,
    agent_id: str,
) -> Answer:
    """Return the events that brought one fact to one player."""
    paths: dict[str, tuple[str, ...]] = {}
    for event in events:
        if isinstance(event, ObservationEvent) and fact_id in _fact_ids(event.observation):
            if event.agent_id not in paths:
                paths[event.agent_id] = (event.event_id,)
            continue
        if not isinstance(event, MessageDeliveryEvent) or event.message != fact_id:
            continue
        source = paths.get(event.sender_id)
        if source is None:
            continue
        step = source + (event.event_id,)
        for recipient_id in event.recipient_ids:
            if recipient_id not in paths:
                paths[recipient_id] = step
    found = paths.get(agent_id)
    if found is None:
        return Answer("unknown")
    return Answer("exact", found)


def _reported_chances(events: tuple[ExecutionEvent, ...], event_id: str) -> Answer:
    """Return the chances written on one belief."""
    event = _find(events, event_id)
    if not isinstance(event, BeliefEvent):
        return Answer("unknown")
    return Answer("exact", _chance_pairs(event))


def _vote_basis(events: tuple[ExecutionEvent, ...], event_id: str) -> Answer:
    """Return the chances and fact names linked from one vote."""
    vote = _find(events, event_id)
    belief = _linked_belief(vote, events)
    if belief is None or not isinstance(vote, ActionEvent):
        return Answer("unknown")
    facts = _facts_for_belief(events, belief, vote.agent_id)
    if facts is None:
        return Answer("unknown")
    return Answer("exact", (_chance_pairs(belief), facts))


def _belief_change(
    events: tuple[ExecutionEvent, ...],
    event_id: str,
    agent_id: str,
) -> Answer:
    """Return the chances before and after one message for one player."""
    message = _find(events, event_id)
    if not isinstance(message, MessageDeliveryEvent):
        return Answer("unknown")
    later = [
        event
        for event in events
        if isinstance(event, BeliefEvent)
        and event.agent_id == agent_id
        and event_id in event.input_event_ids
        and event.sequence_index > message.sequence_index
    ]
    if not later:
        return Answer("unknown")
    after = min(later, key=lambda event: event.sequence_index)
    earlier = [
        event
        for event in events
        if isinstance(event, BeliefEvent)
        and event.agent_id == agent_id
        and event.sequence_index < after.sequence_index
    ]
    if not earlier:
        return Answer("unknown")
    before = max(earlier, key=lambda event: event.sequence_index)
    return Answer("exact", (_chance_pairs(before), _chance_pairs(after)))


def _vote_matches_chances(events: tuple[ExecutionEvent, ...], event_id: str) -> Answer:
    """Return whether the vote picked the route ranked first."""
    vote = _find(events, event_id)
    belief = _linked_belief(vote, events)
    if belief is None or not isinstance(vote, ActionEvent):
        return Answer("unknown")
    return Answer("exact", vote.action == _top_label(belief))


def _decision_action(events: tuple[ExecutionEvent, ...], event_id: str) -> Answer:
    """Return the agent and action recorded on one decision."""
    event = _find(events, event_id)
    if not isinstance(event, ActionEvent):
        return Answer("unknown")
    return Answer("exact", (event.agent_id, event.action))


def _transition_update(events: tuple[ExecutionEvent, ...], event_id: str) -> Answer:
    """Return the update a transition recorded for one outcome."""
    outcome = _find(events, event_id)
    if not isinstance(outcome, OutcomeEvent):
        return Answer("unknown")
    matches = [
        event
        for event in events
        if isinstance(event, TransitionEvent)
        and event.action_event_id == outcome.action_event_id
    ]
    if not matches:
        return Answer("unknown")
    updates = tuple(
        (event.action_event_id, event.input_event_ids)
        for event in matches
    )
    if len(updates) == 1:
        return Answer("exact", updates[0])
    return Answer("candidates", candidates=updates)


def _decision_inputs(events: tuple[ExecutionEvent, ...], event_id: str) -> Answer:
    """Return the input identifiers declared on one decision."""
    event = _find(events, event_id)
    if not isinstance(event, (ActionEvent, BeliefEvent)):
        return Answer("unknown")
    return Answer("exact", event.input_event_ids)


def _event_order(
    events: tuple[ExecutionEvent, ...],
    event_ids: Sequence[str] | None,
) -> Answer:
    """Return event identifiers in sequence order."""
    ordered = tuple(event.event_id for event in events)
    if event_ids is None:
        return Answer("exact", ordered)
    selected = _event_names(event_ids)
    if any(event_id not in ordered for event_id in selected):
        return Answer("unknown")
    rank = {event_id: index for index, event_id in enumerate(ordered)}
    return Answer("exact", tuple(sorted(selected, key=lambda event_id: rank[event_id])))


def _linked_belief(
    vote: ExecutionEvent | None,
    events: tuple[ExecutionEvent, ...],
) -> BeliefEvent | None:
    """Return the one belief a vote points at."""
    if not isinstance(vote, ActionEvent) or not vote.input_event_ids:
        return None
    by_id = {event.event_id: event for event in events}
    found = [
        by_id[item]
        for item in vote.input_event_ids
        if isinstance(by_id.get(item), BeliefEvent)
    ]
    if len(found) != 1 or not isinstance(found[0], BeliefEvent):
        return None
    return found[0]


def _facts_for_belief(
    events: tuple[ExecutionEvent, ...],
    belief: BeliefEvent,
    agent_id: str,
) -> tuple[str, ...] | None:
    """Return the fact names linked from one belief."""
    noted = [
        event
        for event in events
        if isinstance(event, ObservationEvent)
        and event.event_id in belief.input_event_ids
        and event.channel_id == "vote-facts"
    ]
    if len(noted) == 1:
        return tuple(sorted(_fact_ids(noted[0].observation)))
    if noted:
        return None
    facts: set[str] = set()
    saw_deal = False
    for event in events:
        if isinstance(event, ObservationEvent) and event.event_id == f"deal-{agent_id}":
            facts.update(_fact_ids(event.observation))
            saw_deal = True
        delivered = (
            isinstance(event, MessageDeliveryEvent)
            and agent_id in event.recipient_ids
            and event.sequence_index < belief.sequence_index
        )
        if delivered:
            facts.add(event.message)
    if not saw_deal:
        return None
    return tuple(sorted(facts))


def _chance_pairs(belief: BeliefEvent) -> tuple[tuple[str, float], ...]:
    """Return one label and probability pair per option."""
    return tuple(zip(belief.state_labels, belief.probabilities, strict=True))


def _top_label(belief: BeliefEvent) -> str:
    """Return the first label whose chance is the highest."""
    best = 0
    for index, probability in enumerate(belief.probabilities):
        if probability > belief.probabilities[best]:
            best = index
    return belief.state_labels[best]


def _granted(event: ExecutionEvent, fact_id: str) -> frozenset[str]:
    """Return agents who gain one fact from this event."""
    if isinstance(event, ObservationEvent) and fact_id in _fact_ids(event.observation):
        return frozenset({event.agent_id})
    if isinstance(event, MessageDeliveryEvent) and event.message == fact_id:
        return event.recipient_ids
    return frozenset()


def _fact_ids(observation: str) -> frozenset[str]:
    """Split a comma-separated observation into fact identifiers."""
    return frozenset(part for part in observation.split(",") if part)


def _reachable(events: tuple[ExecutionEvent, ...], event_id: str) -> tuple[ExecutionEvent, ...]:
    """Follow declared inputs and return the events in sequence order."""
    by_id = {event.event_id: event for event in events}
    seen: list[str] = []
    pending = [event_id]
    visiting: set[str] = set()
    while pending:
        current = pending.pop()
        if current in visiting:
            continue
        visiting.add(current)
        event = by_id.get(current)
        if event is None or current == event_id:
            inputs = getattr(event, "input_event_ids", ()) if event is not None else ()
            pending.extend(reversed(tuple(inputs)))
            continue
        seen.append(current)
        inputs = getattr(event, "input_event_ids", ())
        pending.extend(reversed(tuple(inputs)))
    found = [by_id[item] for item in seen if item in by_id]
    return tuple(sorted(found, key=lambda event: event.sequence_index))


def _find(events: tuple[ExecutionEvent, ...], event_id: str) -> ExecutionEvent | None:
    """Return the event with one identifier."""
    for event in events:
        if event.event_id == event_id:
            return event
    return None


def _required(value: str | None, name: str) -> str:
    """Return a required non-empty string."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _required_step(value: int | None) -> int:
    """Return a required non-negative model time."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("logical_step must be a non-negative integer")
    return value


def _event_names(event_ids: Sequence[str]) -> tuple[str, ...]:
    """Return the caller's event identifiers."""
    if isinstance(event_ids, str):
        raise ValueError("event_ids must be a sequence of event identifiers")
    names = tuple(event_ids)
    if any(not isinstance(event_id, str) or not event_id for event_id in names):
        raise ValueError("event_ids must contain non-empty strings")
    return names
