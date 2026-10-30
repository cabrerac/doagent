"""Rebuild Hidden Profile events from a session file or from MARBLE logs."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path

from experiments.information_flow.events import (
    ActionEvent,
    BeliefEvent,
    ExecutionEvent,
    MessageDeliveryEvent,
    ObservationEvent,
    OutcomeEvent,
)
from experiments.information_flow.queries import Answer, decode

_DEALT_LINE = re.compile(r"Dealt the private facts\.(.*)")
_ASSIGNMENT = re.compile(r"([A-Za-z0-9_-]+)=([^ ]*)")
_DISCLOSE = re.compile(r"kind=disclose fact=([^ ]*) recipients=([^ ]*)")


def parse_doagent(records_path: str | Path) -> tuple[ExecutionEvent, ...]:
    """Rebuild events from an exported session file.

    Args:
        records_path: Path of the records file written by the session runner.

    Returns:
        Deal observations, disclosures, votes, and any links the file states.

    Raises:
        ValueError: The file has no outcome records.
        ValueError: One vote links to the group result more than once.
    """
    document = json.loads(Path(records_path).read_text(encoding="utf-8"))
    updates = document.get("agent_update") or []
    outcomes = sorted(
        document.get("outcome") or [],
        key=lambda record: int(record["payload"]["round"]),
    )
    if not outcomes:
        raise ValueError("the session file has no outcome records")
    first_round = int(outcomes[0]["payload"]["round"])
    dealt = {
        record["actor"]: _dealt_ids(_observation(record))
        for record in updates
        if _round_of(record) == first_round
    }
    rounds = [record["payload"]["actions"] for record in outcomes]
    played = _play_events(dealt, rounds, "parsed-doagent", _vote_notes(document))
    return _with_session_links(document, played)


def parse_marble(
    log_dir: str | Path,
    logs: Sequence[str | Path] | None = None,
) -> tuple[ExecutionEvent, ...]:
    """Rebuild events from the MARBLE logs an analyst may open.

    Args:
        log_dir: Directory that contains the component log files.
        logs: Log files the analyst may open.
            Omit this to open every log in the directory.

    Returns:
        Deal observations, disclosures, and votes present in those files.
        A vote basis is included when the vote line states one.

    Raises:
        ValueError: A selected log cannot be read.
    """
    folder = Path(log_dir)
    if logs is None:
        selected = [folder / "HiddenProfileEnv.log"]
        selected.extend(sorted(folder.glob("HiddenProfileAgent.*.log")))
    else:
        selected = [Path(path) for path in logs]
    env_logs = [path for path in selected if path.name == "HiddenProfileEnv.log"]
    paths = [
        path
        for path in selected
        if path.name.startswith("HiddenProfileAgent.") and path.suffix == ".log"
    ]
    dealt = _dealt_from_log(env_logs[0]) if env_logs else {}
    if logs is None and not paths:
        raise ValueError("the log directory has no agent logs")
    if not dealt and not paths:
        return ()
    by_agent = {_agent_id(path): _actions_from_log(path) for path in paths}
    width = {len(actions) for actions in by_agent.values()}
    if len(width) != 1:
        raise ValueError("agent logs must cover the same rounds")
    count = width.pop()
    rounds = [
        {agent_id: actions[index] for agent_id, actions in by_agent.items()}
        for index in range(count)
    ]
    return _play_events(dealt, rounds, "parsed-marble", _notes_from_rounds(rounds))


def vote_bases(
    events: Sequence[ExecutionEvent],
    agents: Sequence[str],
) -> tuple[Answer, ...]:
    """Return what each vote was based on, in agent order.

    A stated basis names the chances and the fact names.
    A vote with no such note is not stated.

    Args:
        events: Ordered events read from one artifact or from the rules.
        agents: Agent identifiers, in answer order.

    Returns:
        One answer per agent.
    """
    return tuple(
        decode(events, "vote_basis", event_id=f"vote-{agent_id}")
        for agent_id in agents
    )


def _play_events(
    dealt: Mapping[str, tuple[str, ...]],
    rounds: Sequence[Mapping[str, dict]],
    episode_id: str,
    notes: Mapping[str, tuple[tuple[str, ...], tuple[float, ...], tuple[str, ...]]] | None = None,
) -> tuple[ExecutionEvent, ...]:
    """Build events from dealt facts and one action mapping per round.

    Args:
        dealt: Agent identifier to the fact ids in the opening hand.
        rounds: One action mapping per round, in play order.
        episode_id: Identifier stored on each event.
        notes: Agent identifier to the chances and fact names behind that vote.
            Omit this when the artifact does not state a basis.

    Returns:
        Deal observations, disclosures, votes, and any stated vote bases.
    """
    events: list[ExecutionEvent] = []
    sequence_index = 1
    for agent_id in sorted(dealt):
        events.append(
            ObservationEvent(
                episode_id=episode_id,
                event_id=f"deal-{agent_id}",
                logical_step=0,
                sequence_index=sequence_index,
                agent_id=agent_id,
                observation=",".join(dealt[agent_id]),
                channel_id="deal",
                source_state_event_id="absent",
            )
        )
        sequence_index += 1
    for index, actions in enumerate(rounds):
        for agent_id in sorted(actions):
            action = actions[agent_id]
            kind = action.get("kind")
            if kind == "disclose" and action.get("fact_id"):
                recipients = action.get("recipients") or ()
                events.append(
                    MessageDeliveryEvent(
                        episode_id=episode_id,
                        event_id=f"disclosure-{index}-{agent_id}",
                        logical_step=index,
                        sequence_index=sequence_index,
                        sender_id=agent_id,
                        message_id=f"disclosure-{index}-{agent_id}",
                        message=str(action["fact_id"]),
                        recipient_ids=frozenset(str(item) for item in recipients),
                    )
                )
                sequence_index += 1
            elif kind == "vote":
                basis = None if notes is None else notes.get(agent_id)
                input_ids: tuple[str, ...] = ()
                if basis is not None:
                    labels, probabilities, fact_ids = basis
                    sequence_index = _append_basis(
                        events,
                        episode_id,
                        agent_id,
                        index,
                        sequence_index,
                        labels,
                        probabilities,
                        fact_ids,
                    )
                    input_ids = (f"belief-vote-{agent_id}",)
                events.append(
                    ActionEvent(
                        episode_id=episode_id,
                        event_id=f"vote-{agent_id}",
                        logical_step=index,
                        sequence_index=sequence_index,
                        agent_id=agent_id,
                        action=str(action.get("option")),
                        input_event_ids=input_ids,
                    )
                )
                sequence_index += 1
    return tuple(events)


def _with_session_links(
    document: Mapping[str, object],
    events: tuple[ExecutionEvent, ...],
) -> tuple[ExecutionEvent, ...]:
    """Add the group result and the chance changes the session file states.

    Args:
        document: Exported session records.
        events: Deal observations, disclosures, and votes already rebuilt.

    Returns:
        Those events, plus a group result and chance changes when the file states them.

    Raises:
        ValueError: One vote links to the group result more than once.
    """
    outcomes = [
        record
        for record in sorted(
            _records(document, "outcome"),
            key=lambda record: int(record["payload"]["round"]),
        )
        if isinstance(record, Mapping)
    ]
    episode_id = events[0].episode_id if events else "parsed-doagent"
    messages = [
        event for event in events if isinstance(event, MessageDeliveryEvent)
    ]
    beliefs: dict[int, tuple[BeliefEvent, ...]] = {}
    for index, record in enumerate(outcomes):
        if _is_vote_outcome(record):
            continue
        stated = _round_beliefs(record, index, messages, episode_id)
        if stated:
            beliefs[index] = stated
    return _splice_session(events, beliefs, _group_outcome(document, outcomes, episode_id))


def _round_beliefs(
    record: Mapping[str, object],
    index: int,
    messages: Sequence[MessageDeliveryEvent],
    episode_id: str,
) -> tuple[BeliefEvent, ...]:
    """Return the chances stored on one disclosure result.

    Args:
        record: One outcome record.
        index: Play order of that outcome.
        messages: Disclosures already rebuilt from the file.
        episode_id: Identifier stored on each event.

    Returns:
        One belief per player whose result states chances.
        Empty when the result states none.
    """
    payload = record.get("payload")
    if not isinstance(payload, Mapping):
        return ()
    observations = payload.get("observations")
    if not isinstance(observations, Mapping):
        return ()
    delivered = [message for message in messages if message.logical_step == index]
    found: list[BeliefEvent] = []
    for agent_id, observation in observations.items():
        if not isinstance(agent_id, str) or not agent_id:
            continue
        if not isinstance(observation, Mapping):
            continue
        stated = _stated_chances(observation)
        if stated is None:
            continue
        labels, probabilities = stated
        received = tuple(
            message.event_id
            for message in delivered
            if agent_id in message.recipient_ids
        )
        found.append(
            BeliefEvent(
                episode_id=episode_id,
                event_id=f"belief-{index}-{agent_id}",
                logical_step=index,
                sequence_index=0,
                agent_id=agent_id,
                state_labels=labels,
                probabilities=probabilities,
                input_event_ids=received or (f"deal-{agent_id}",),
            )
        )
    return tuple(found)


def _stated_chances(
    observation: Mapping[str, object],
) -> tuple[tuple[str, ...], tuple[float, ...]] | None:
    """Return option names and chances when the observation stores both."""
    labels = _text_items(observation.get("options"))
    chances = _chances(observation.get("belief"))
    if labels is None or chances is None:
        return None
    if not labels or len(labels) != len(chances) or len(set(labels)) != len(labels):
        return None
    return labels, chances


def _group_outcome(
    document: Mapping[str, object],
    outcomes: Sequence[Mapping[str, object]],
    episode_id: str,
) -> OutcomeEvent | None:
    """Return the group result when every vote links to it.

    Args:
        document: Exported session records.
        outcomes: Outcome records in play order.
        episode_id: Identifier stored on the result.

    Returns:
        The group result.
        None when a vote has no link.

    Raises:
        ValueError: One vote links to the group result more than once.
    """
    found = [
        (index, record)
        for index, record in enumerate(outcomes)
        if _is_vote_outcome(record)
    ]
    if len(found) != 1:
        return None
    index, record = found[0]
    payload = record.get("payload")
    vote_id = record.get("id")
    if not isinstance(payload, Mapping) or not isinstance(vote_id, str) or not vote_id:
        return None
    actions = payload.get("actions")
    if not isinstance(actions, Mapping) or not actions:
        return None
    updates = {
        str(item["id"]): item
        for item in _records(document, "agent_update")
        if isinstance(item, Mapping) and item.get("id") is not None
    }
    linked: dict[str, str] = {}
    for trace in _records(document, "trace"):
        if not isinstance(trace, Mapping):
            continue
        body = trace.get("payload")
        if not isinstance(body, Mapping) or body.get("to_id") != vote_id:
            continue
        update = updates.get(str(body.get("enabled_by_id")))
        if not isinstance(update, Mapping):
            continue
        agent_id = update.get("actor")
        action = actions.get(agent_id)
        if not isinstance(agent_id, str) or not isinstance(action, Mapping):
            continue
        if action.get("kind") != "vote":
            continue
        if agent_id in linked:
            raise ValueError("a vote links to the group result more than once")
        linked[agent_id] = f"vote-{agent_id}"
    if set(linked) != {agent_id for agent_id in actions if isinstance(agent_id, str)}:
        return None
    names = tuple(linked[str(agent_id)] for agent_id in actions)
    label = _group_label(actions, payload.get("observations"))
    if label is None or len(names) != len(actions):
        return None
    return OutcomeEvent(
        episode_id=episode_id,
        event_id="outcome-group",
        logical_step=index,
        sequence_index=0,
        agent_id="group",
        outcome=label,
        action_event_id=names[0],
        contributing_event_ids=names,
    )


def _group_label(
    actions: Mapping[str, object],
    observations: object,
) -> str | None:
    """Return the group choice named by the stored votes and option order."""
    chosen: list[str] = []
    for action in actions.values():
        if not isinstance(action, Mapping):
            return None
        option = action.get("option")
        if not isinstance(option, str) or not option:
            return None
        chosen.append(option)
    options = _stored_options(observations)
    if options is None:
        if len(set(chosen)) == 1:
            return chosen[0]
        return None
    counts = {option: 0 for option in options}
    for option in chosen:
        if option not in counts:
            return None
        counts[option] += 1
    best = max(counts.values())
    for option in options:
        if counts[option] == best:
            return option
    return None


def _stored_options(observations: object) -> tuple[str, ...] | None:
    """Return the option order stored on a round result."""
    if not isinstance(observations, Mapping):
        return None
    for observation in observations.values():
        if not isinstance(observation, Mapping):
            continue
        labels = _text_items(observation.get("options"))
        if labels:
            return labels
    return None


def _splice_session(
    events: tuple[ExecutionEvent, ...],
    beliefs: Mapping[int, tuple[BeliefEvent, ...]],
    outcome: OutcomeEvent | None,
) -> tuple[ExecutionEvent, ...]:
    """Place each chance change after its round and the group result last.

    Args:
        events: Deal observations, disclosures, and votes.
        beliefs: Play order to the chances stated on that round.
        outcome: Group result.
            Omit this when the file does not link every vote.

    Returns:
        The events in play order, with positions rewritten from the start.
    """
    deals: list[ExecutionEvent] = []
    messages: dict[int, list[ExecutionEvent]] = {}
    rest: list[ExecutionEvent] = []
    for event in events:
        if isinstance(event, ObservationEvent) and event.channel_id == "deal":
            deals.append(event)
            continue
        if isinstance(event, MessageDeliveryEvent):
            messages.setdefault(event.logical_step, []).append(event)
            continue
        rest.append(event)
    ordered: list[ExecutionEvent] = list(deals)
    for step in sorted(set(messages) | set(beliefs)):
        ordered.extend(messages.get(step, []))
        ordered.extend(beliefs.get(step, ()))
    ordered.extend(rest)
    if outcome is not None:
        ordered.append(outcome)
    return tuple(
        replace(event, sequence_index=index)
        for index, event in enumerate(ordered, start=1)
    )


def _observation(record: Mapping[str, object]) -> Mapping[str, object]:
    """Return the observation stored on one agent update."""
    payload = record.get("payload")
    if not isinstance(payload, Mapping):
        return {}
    knowledge = payload.get("local_knowledge")
    if isinstance(knowledge, Mapping) and isinstance(knowledge.get("observation"), Mapping):
        return knowledge["observation"]
    return {}


def _round_of(record: Mapping[str, object]) -> int | None:
    """Return the session round stored on one agent update."""
    payload = record.get("payload")
    if not isinstance(payload, Mapping):
        return None
    decision = payload.get("decision")
    if not isinstance(decision, Mapping):
        return None
    request = decision.get("request")
    if not isinstance(request, Mapping):
        return None
    context = request.get("context")
    if not isinstance(context, Mapping):
        return None
    round_id = context.get("round")
    if isinstance(round_id, bool) or not isinstance(round_id, int):
        return None
    return round_id


def _dealt_ids(observation: Mapping[str, object]) -> tuple[str, ...]:
    """Return the shared and dealt fact ids in one opening observation."""
    held = observation.get("held_facts") or ()
    fact_ids = [
        str(fact["fact_id"])
        for fact in held
        if isinstance(fact, Mapping) and fact.get("origin") in ("shared", "dealt")
    ]
    return tuple(sorted(fact_ids))


def _dealt_from_log(path: Path) -> dict[str, tuple[str, ...]]:
    """Read the private-fact assignment from the environment log."""
    if not path.is_file():
        raise ValueError("the environment log is missing")
    for line in path.read_text(encoding="utf-8").splitlines():
        matched = _DEALT_LINE.search(line)
        if matched is None:
            continue
        assigned = {
            agent_id: tuple(fact_id for fact_id in facts.split(",") if fact_id)
            for agent_id, facts in _ASSIGNMENT.findall(matched.group(1))
        }
        if assigned:
            return assigned
    raise ValueError("the environment log does not name the dealt facts")


def _actions_from_log(path: Path) -> list[dict[str, object]]:
    """Read the choices from one agent log, in order."""
    actions = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = dict(_ASSIGNMENT.findall(line))
        if fields.get("kind") == "vote":
            actions.append(_vote_action(fields))
            continue
        disclosed = _DISCLOSE.search(line)
        if disclosed is not None:
            fact_id = disclosed.group(1)
            recipients = disclosed.group(2)
            actions.append(
                {
                    "kind": "disclose",
                    "fact_id": fact_id or None,
                    "recipients": [
                        recipient for recipient in recipients.split(",") if recipient
                    ],
                }
            )
            continue
    if not actions:
        raise ValueError(f"the agent log names no actions: {path.name}")
    return actions


def _notes_from_rounds(
    rounds: Sequence[Mapping[str, Mapping[str, object]]],
) -> dict[str, tuple[tuple[str, ...], tuple[float, ...], tuple[str, ...]]]:
    """Read chances and fact names stated on the vote actions."""
    notes: dict[str, tuple[tuple[str, ...], tuple[float, ...], tuple[str, ...]]] = {}
    for actions in rounds:
        for agent_id, action in actions.items():
            if action.get("kind") != "vote":
                continue
            note = _note_from_action(action)
            if note is None:
                continue
            if agent_id in notes:
                raise ValueError("a vote states more than one basis")
            notes[agent_id] = note
    return notes


def _vote_action(fields: Mapping[str, str]) -> dict[str, object]:
    """Return one vote, including chances and fact names when the line states them."""
    option = fields.get("option")
    if not option:
        raise ValueError("a vote line must name an option")
    action: dict[str, object] = {"kind": "vote", "option": option}
    if "options" in fields:
        action["options"] = _text_items(fields["options"])
    if "belief" in fields:
        action["belief"] = _chances(fields["belief"])
    if "facts" in fields:
        action["facts"] = _text_items(fields["facts"])
    return action


def _note_from_action(
    action: Mapping[str, object],
) -> tuple[tuple[str, ...], tuple[float, ...], tuple[str, ...]] | None:
    """Return chances and fact names when one vote action states all three parts."""
    labels = _text_items(action.get("options"))
    chances = _chances(action.get("belief"))
    fact_ids = _text_items(action.get("facts"))
    if labels is None or chances is None or fact_ids is None:
        return None
    if not labels or len(labels) != len(chances) or not fact_ids:
        return None
    return labels, chances, tuple(sorted(set(fact_ids)))


def _text_items(value: object) -> tuple[str, ...] | None:
    """Return text items from a list or a comma-separated string."""
    if isinstance(value, str):
        return tuple(part for part in value.split(",") if part)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(part) for part in value if str(part))
    return None


def _chances(value: object) -> tuple[float, ...] | None:
    """Return chances from a list of numbers or a comma-separated string."""
    if isinstance(value, str):
        parts = [part for part in value.split(",") if part]
        return tuple(float(part) for part in parts)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if any(isinstance(part, bool) or not isinstance(part, (int, float)) for part in value):
            return None
        return tuple(float(part) for part in value)
    return None


def _vote_notes(
    document: Mapping[str, object],
) -> dict[str, tuple[tuple[str, ...], tuple[float, ...], tuple[str, ...]]]:
    """Read each vote's chances and fact names from the linked decision note."""
    updates = {
        str(record["id"]): record
        for record in _records(document, "agent_update")
        if isinstance(record, Mapping) and record.get("id") is not None
    }
    vote_ids = [
        str(record["id"])
        for record in _records(document, "outcome")
        if isinstance(record, Mapping) and _is_vote_outcome(record)
    ]
    if len(vote_ids) != 1:
        return {}
    notes: dict[str, tuple[tuple[str, ...], tuple[float, ...], tuple[str, ...]]] = {}
    for record in _records(document, "trace"):
        if not isinstance(record, Mapping):
            continue
        payload = record.get("payload")
        if not isinstance(payload, Mapping) or payload.get("to_id") != vote_ids[0]:
            continue
        update = updates.get(str(payload.get("enabled_by_id")))
        if update is None:
            continue
        agent_id = update.get("actor")
        note = _note_from_observation(_observation(update))
        if not isinstance(agent_id, str) or not agent_id or note is None:
            continue
        if agent_id in notes:
            raise ValueError("a vote links to more than one decision note")
        notes[agent_id] = note
    return notes


def _records(document: Mapping[str, object], kind: str) -> tuple[object, ...]:
    """Return the stored records of one kind."""
    found = document.get(kind) or ()
    if isinstance(found, Sequence) and not isinstance(found, (str, bytes)):
        return tuple(found)
    return ()


def _is_vote_outcome(record: Mapping[str, object]) -> bool:
    """Return whether every action on this outcome is a vote."""
    payload = record.get("payload")
    if not isinstance(payload, Mapping):
        return False
    actions = payload.get("actions")
    if not isinstance(actions, Mapping) or not actions:
        return False
    return all(
        isinstance(action, Mapping) and action.get("kind") == "vote"
        for action in actions.values()
    )


def _note_from_observation(
    observation: Mapping[str, object],
) -> tuple[tuple[str, ...], tuple[float, ...], tuple[str, ...]] | None:
    """Return chances and fact names from one vote observation."""
    if observation.get("phase") != "vote":
        return None
    options = observation.get("options")
    belief = observation.get("belief")
    held = observation.get("held_facts")
    if not isinstance(options, Sequence) or isinstance(options, (str, bytes)):
        return None
    if not isinstance(belief, Sequence) or isinstance(belief, (str, bytes)):
        return None
    if not isinstance(held, Sequence) or isinstance(held, (str, bytes)):
        return None
    labels = tuple(str(option) for option in options)
    if not labels or len(labels) != len(tuple(belief)):
        return None
    probabilities = tuple(float(chance) for chance in belief)
    fact_ids = tuple(
        sorted(
            {
                str(fact["fact_id"])
                for fact in held
                if isinstance(fact, Mapping) and fact.get("fact_id")
            }
        )
    )
    if not fact_ids:
        return None
    return labels, probabilities, fact_ids


def _append_basis(
    events: list[ExecutionEvent],
    episode_id: str,
    agent_id: str,
    logical_step: int,
    sequence_index: int,
    labels: tuple[str, ...],
    probabilities: tuple[float, ...],
    fact_ids: tuple[str, ...],
) -> int:
    """Append the fact names and the chances that sit behind one vote."""
    events.append(
        ObservationEvent(
            episode_id=episode_id,
            event_id=f"vote-facts-{agent_id}",
            logical_step=logical_step,
            sequence_index=sequence_index,
            agent_id=agent_id,
            observation=",".join(fact_ids),
            channel_id="vote-facts",
            source_state_event_id="absent",
        )
    )
    sequence_index += 1
    events.append(
        BeliefEvent(
            episode_id=episode_id,
            event_id=f"belief-vote-{agent_id}",
            logical_step=logical_step,
            sequence_index=sequence_index,
            agent_id=agent_id,
            state_labels=labels,
            probabilities=probabilities,
            input_event_ids=(f"vote-facts-{agent_id}",),
        )
    )
    return sequence_index + 1


def _agent_id(path: Path) -> str:
    """Return the agent identifier encoded in a log file name."""
    prefix = "HiddenProfileAgent."
    suffix = ".log"
    name = path.name
    if not name.startswith(prefix) or not name.endswith(suffix):
        raise ValueError(f"unexpected agent log name: {name}")
    return name[len(prefix):-len(suffix)]
