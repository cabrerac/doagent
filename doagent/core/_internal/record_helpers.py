"""Record factory helpers: create agent_update, trace, outcome, and explanation records.

Used internally by RecordWriter, FunctionAgent, and StubAgent. Not part of the
public Session API; users configure recording via Session and RunConfig.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from ...records import ExplanationRecord, SimpleRecord


def new_record(
    *,
    actor: str,
    kind: str,
    payload: Dict[str, Any],
    provenance: Optional[Dict[str, Any]] = None,
    accountability: Optional[Dict[str, Any]] = None,
    record_id: Optional[str] = None,
) -> SimpleRecord:
    """Create a record with a standard envelope."""
    timestamp = datetime.now(timezone.utc).isoformat()
    return SimpleRecord(
        id=record_id or str(uuid4()),
        timestamp=timestamp,
        actor=actor,
        kind=kind,
        payload=payload,
        provenance=provenance or {},
        accountability=accountability or {},
    )


def new_explanation_record(
    *,
    actor: str,
    decision_id: str,
    summary: str,
    details: Optional[str] = None,
    evidence: Optional[list[str]] = None,
    provenance: Optional[Dict[str, Any]] = None,
    record_id: Optional[str] = None,
) -> ExplanationRecord:
    """Create an explanation record linked to a decision."""
    payload: Dict[str, Any] = {"decision_id": decision_id, "summary": summary}
    if details is not None:
        payload["details"] = details
    if evidence is not None:
        payload["evidence"] = evidence
    record = new_record(
        actor=actor,
        kind="explanation",
        payload=payload,
        provenance=provenance,
        record_id=record_id,
    )
    return ExplanationRecord(**record.__dict__)


def new_trace_record(
    *,
    actor: str,
    from_id: str,
    to_id: str,
    enabled_by_id: str,
    relation: str = "enables",
    round_: Optional[int] = None,
    trace_actor: Optional[str] = None,
    trace_timestamp: Optional[str] = None,
    notes: Optional[str] = None,
    provenance: Optional[Dict[str, Any]] = None,
    accountability: Optional[Dict[str, Any]] = None,
    record_id: Optional[str] = None,
) -> SimpleRecord:
    """Create a trace record linking environment outcomes via agent_update."""
    payload: Dict[str, Any] = {
        "from_id": from_id,
        "to_id": to_id,
        "enabled_by_id": enabled_by_id,
        "relation": relation,
    }
    if round_ is not None:
        payload["round"] = round_
    if trace_actor is not None:
        payload["actor"] = trace_actor
    if trace_timestamp is not None:
        payload["timestamp"] = trace_timestamp
    if notes is not None:
        payload["notes"] = notes
    return new_record(
        actor=actor,
        kind="trace",
        payload=payload,
        provenance=provenance,
        accountability=accountability,
        record_id=record_id,
    )


def new_agent_update_record(
    *,
    actor: str,
    local_knowledge: Dict[str, Any],
    decision: Dict[str, Any],
    payload_type: Optional[str] = None,
    provenance: Optional[Dict[str, Any]] = None,
    accountability: Optional[Dict[str, Any]] = None,
    record_id: Optional[str] = None,
) -> SimpleRecord:
    """Create an agent_update record with local_knowledge and decision.

    decision should contain request, response, and optionally explanation.
    Do not duplicate provenance/accountability inside decision.response.
    """
    payload: Dict[str, Any] = {
        "local_knowledge": local_knowledge,
        "decision": decision,
    }
    if payload_type is not None:
        payload["type"] = payload_type
    return new_record(
        actor=actor,
        kind="agent_update",
        payload=payload,
        provenance=provenance,
        accountability=accountability,
        record_id=record_id,
    )
