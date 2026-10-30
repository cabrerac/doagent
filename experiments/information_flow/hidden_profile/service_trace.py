"""Write and read an optional structured service trace for one MARBLE run."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

from experiments.information_flow.events import ExecutionEvent
from experiments.information_flow.hidden_profile.parse import (
    _notes_from_rounds,
    _play_events,
)
from experiments.information_flow.hidden_profile.reading import ReadingCost

TRACE_NAME = "service_trace.jsonl"
PARENT_ID = "engine-run"
LINE_FIELDS = (
    "callee",
    "caller",
    "message_id",
    "operation",
    "parent_id",
    "payload",
    "service",
    "status",
    "timestamp",
)


class ServiceTrace:
    """Append one JSON line for each call the engine makes.

    Args:
        path: File that receives the lines.
    """

    def __init__(self, path: str | Path) -> None:
        """Open the trace and record the engine run as the parent call."""
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w", encoding="utf-8")
        self._line(
            service="HiddenProfileEngine",
            caller="HiddenProfileEngine",
            callee="HiddenProfileEngine",
            operation="run",
            message_id=PARENT_ID,
            payload={},
            parent_id=None,
        )

    def __enter__(self) -> ServiceTrace:
        """Return this trace."""
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Close the trace file."""
        del exc_type, exc, traceback
        self.close()

    def deal(self, observations: Mapping[str, Mapping[str, object]]) -> None:
        """Record the deal call and the private facts each agent was dealt.

        Args:
            observations: Agent identifier to that agent's opening observation.
        """
        self._line(
            service="HiddenProfileEnv",
            caller="HiddenProfileEngine",
            callee="HiddenProfileEnv",
            operation="deal",
            message_id="deal",
            payload=_dealt_payload(observations),
            parent_id=PARENT_ID,
        )

    def action(self, agent_id: str, action: Mapping[str, object], round_index: int) -> None:
        """Record one agent call and the action it returned.

        Args:
            agent_id: Identifier of the agent.
            action: Action returned by that agent.
            round_index: Zero-based round of this call.
        """
        service = f"HiddenProfileAgent.{agent_id}"
        kind = str(action.get("kind") or "call")
        message_id = _message_id(kind, agent_id, round_index)
        self._line(
            service=service,
            caller="HiddenProfileEngine",
            callee=service,
            operation=kind,
            message_id=message_id,
            payload=_action_payload(action),
            parent_id=PARENT_ID,
        )

    def close(self) -> None:
        """Close the trace file."""
        self._handle.close()

    def _line(
        self,
        service: str,
        caller: str,
        callee: str,
        operation: str,
        message_id: str,
        payload: Mapping[str, object],
        parent_id: str | None,
    ) -> None:
        """Append one call line."""
        record = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "service": service,
            "caller": caller,
            "callee": callee,
            "operation": operation,
            "message_id": message_id,
            "payload": payload,
            "status": "ok",
            "parent_id": parent_id,
        }
        self._handle.write(json.dumps(record, sort_keys=True))
        self._handle.write("\n")


def parse_service_trace(path: str | Path) -> tuple[ExecutionEvent, ...]:
    """Rebuild events from one structured service trace.

    Args:
        path: Path of the trace file.

    Returns:
        Deal observations, disclosures, and votes present in the file.
        A vote basis is included when the vote call states one.

    Raises:
        ValueError: The file is missing or does not contain one complete deal.
    """
    trace_path = Path(path)
    if not trace_path.is_file():
        raise ValueError("the service trace is missing")
    lines = [
        _load_line(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    deals = [line for line in lines if line["operation"] == "deal"]
    if len(deals) != 1:
        raise ValueError("the service trace must contain one deal")
    dealt = {
        str(agent_id): tuple(str(fact_id) for fact_id in fact_ids)
        for agent_id, fact_ids in deals[0]["payload"].items()
    }
    calls = [line for line in lines if line["operation"] in ("disclose", "vote")]
    if not dealt or len(calls) % len(dealt) != 0:
        raise ValueError("the service trace does not cover equal rounds")
    width = len(dealt)
    rounds = [
        {
            _agent_id(line["service"]): dict(line["payload"])
            for line in calls[start:start + width]
        }
        for start in range(0, len(calls), width)
    ]
    return _play_events(
        dealt,
        rounds,
        "parsed-service-trace",
        _notes_from_rounds(rounds),
    )


def trace_reading(path: str | Path) -> ReadingCost:
    """Count the cost of reading one structured service trace.

    Args:
        path: Path of the trace file.

    Returns:
        One file, its size, and no joins.

    Raises:
        ValueError: The trace file is missing.
    """
    trace_path = Path(path)
    if not trace_path.is_file():
        raise ValueError("the service trace is missing")
    return ReadingCost(files_opened=1, bytes_read=trace_path.stat().st_size, joins=0)


def _dealt_payload(
    observations: Mapping[str, Mapping[str, object]],
) -> dict[str, list[str]]:
    """Return the private fact ids dealt to each agent."""
    payload: dict[str, list[str]] = {}
    for agent_id, observation in observations.items():
        held = observation.get("held_facts") or ()
        payload[str(agent_id)] = [
            str(fact["fact_id"])
            for fact in held
            if isinstance(fact, Mapping) and fact.get("origin") == "dealt"
        ]
    return payload


def _action_payload(action: Mapping[str, object]) -> dict[str, object]:
    """Return one action as JSON-ready fields."""
    kind = action.get("kind")
    if kind == "disclose":
        recipients = action.get("recipients") or ()
        return {
            "kind": "disclose",
            "fact_id": action.get("fact_id"),
            "recipients": [str(recipient) for recipient in recipients],
        }
    if kind == "vote":
        return {"kind": "vote", "option": action.get("option")}
    return {"kind": kind}


def _message_id(kind: str, agent_id: str, round_index: int) -> str:
    """Return the message identifier for one agent call."""
    if kind == "vote":
        return f"vote-{agent_id}"
    if kind == "disclose":
        return f"disclosure-{round_index}-{agent_id}"
    return f"call-{round_index}-{agent_id}"


def _load_line(line: str) -> dict[str, object]:
    """Return one trace line after checking its fields."""
    record = json.loads(line)
    if not isinstance(record, dict) or tuple(sorted(record)) != LINE_FIELDS:
        raise ValueError("a service trace line has an unexpected field set")
    return record


def _agent_id(service: object) -> str:
    """Return the agent identifier encoded in a service name."""
    prefix = "HiddenProfileAgent."
    if not isinstance(service, str) or not service.startswith(prefix):
        raise ValueError("a service trace call does not name an agent")
    return service[len(prefix):]
