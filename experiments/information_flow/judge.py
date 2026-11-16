"""Ask one judge the same questions from traces and from records.

The judge is a model caller.
The exact answers used for the check come from the neutral events.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from experiments.information_flow.events import (
    ActionEvent,
    ExecutionEvent,
    MessageDeliveryEvent,
    ObservationEvent,
)
from experiments.information_flow.model_trace import reject_record_ids
from experiments.information_flow.queries import Answer


@dataclass(frozen=True)
class JudgeMismatch:
    """Name one question the judge did not match.

    Args:
        reading: traces or records.
        question: Question text sent to the judge.
        expected_kind: Kind of the exact answer.
        judged_kind: Kind of the judge's answer.
    """

    reading: str
    question: str
    expected_kind: str
    judged_kind: str


def trace_evidence(events: Sequence[ExecutionEvent]) -> str:
    """Render the text a trace reading may show.

    Args:
        events: Neutral events from one run.

    Returns:
        One line per observation, message, and action.

    Raises:
        ValueError: The rendered text contains a record id.
    """
    lines: list[str] = []
    for event in events:
        if isinstance(event, ObservationEvent):
            lines.append(
                f"observation {event.agent_id} saw {event.observation}"
            )
        elif isinstance(event, MessageDeliveryEvent):
            recipients = ",".join(sorted(event.recipient_ids))
            lines.append(
                f"message {event.sender_id} sent {event.message} to {recipients}"
            )
        elif isinstance(event, ActionEvent):
            lines.append(f"action {event.agent_id} chose {event.action}")
    text = "\n".join(lines)
    reject_record_ids(text)
    return text


def record_evidence(document: Mapping[str, object]) -> str:
    """Render the session export a record reading may show.

    Args:
        document: Exported session records.

    Returns:
        The export as JSON text.
    """
    return json.dumps(document, sort_keys=True, default=str)


def judge_prompt(question: str, evidence: str, reading: str) -> str:
    """Build the prompt for one question and one reading.

    Args:
        question: Question in ordinary language.
        evidence: Trace text or record text.
        reading: traces or records.

    Returns:
        The prompt sent to the judge.

    Raises:
        ValueError: The reading name is not traces or records.
    """
    if reading not in ("traces", "records"):
        raise ValueError("reading must be traces or records")
    return (
        f"Reading: {reading}\n"
        f"Question: {question}\n"
        "Reply with JSON using kind exact, unknown, or candidates.\n"
        f"Evidence:\n{evidence}"
    )


def parse_judge_answer(text: str) -> Answer:
    """Read one judge reply.

    Args:
        text: JSON object with kind and, when needed, value or candidates.

    Returns:
        The answer the judge gave.

    Raises:
        ValueError: The reply is not a usable answer.
    """
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("the judge reply must be JSON") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("the judge reply must be a JSON object")
    kind = payload.get("kind")
    if kind == "unknown":
        return Answer("unknown")
    if kind == "exact":
        return Answer("exact", _structured(payload.get("value")))
    if kind == "candidates":
        raw = payload.get("candidates")
        if not isinstance(raw, list):
            raise ValueError("candidates must be a list")
        return Answer("candidates", candidates=tuple(_structured(item) for item in raw))
    raise ValueError("kind must be exact, unknown, or candidates")


def judge_one(
    caller: Callable[[str], str],
    question: str,
    evidence: str,
    reading: str,
) -> Answer:
    """Ask the judge one question about one reading.

    Args:
        caller: Function that sends one prompt and returns the output text.
        question: Question in ordinary language.
        evidence: Trace text or record text.
        reading: traces or records.

    Returns:
        The parsed judge answer.
    """
    return parse_judge_answer(caller(judge_prompt(question, evidence, reading)))


def judge_mismatches(
    caller: Callable[[str], str],
    questions: Sequence[tuple[str, Answer]],
    evidence_by_reading: Mapping[str, str],
) -> tuple[JudgeMismatch, ...]:
    """Compare the judge with the exact answers on each reading.

    The same question text is sent for every reading.

    Args:
        caller: Judge model.
        questions: Question text paired with its exact answer.
        evidence_by_reading: traces and records text.

    Returns:
        One entry for each question the judge did not match.
    """
    found: list[JudgeMismatch] = []
    for reading, evidence in evidence_by_reading.items():
        for question, expected in questions:
            judged = judge_one(caller, question, evidence, reading)
            if not _same_answer(expected, judged):
                found.append(
                    JudgeMismatch(
                        reading=reading,
                        question=question,
                        expected_kind=expected.kind,
                        judged_kind=judged.kind,
                    )
                )
    return tuple(found)


def _structured(value: object) -> object:
    """Turn JSON lists into tuples so they can match stored answers."""
    if isinstance(value, list):
        return tuple(_structured(item) for item in value)
    return value


def _same_answer(expected: Answer, judged: Answer) -> bool:
    """Return whether two answers carry the same content."""
    if expected.kind != judged.kind:
        return False
    return _canonical(expected.value) == _canonical(judged.value) and _canonical(
        expected.candidates
    ) == _canonical(judged.candidates)


def _canonical(value: object) -> object:
    """Return a comparable form of an answer value."""
    if isinstance(value, (frozenset, set)):
        return tuple(sorted((_canonical(item) for item in value), key=repr))
    if isinstance(value, (tuple, list)):
        return tuple(_canonical(item) for item in value)
    return value
