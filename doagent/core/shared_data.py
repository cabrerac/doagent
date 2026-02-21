"""Shared data adapters and record helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional
from uuid import uuid4

from ..interface.shared_data import SharedDataAdapter
from ..records import ExplanationRecord, SimpleRecord

class InMemorySharedData(SharedDataAdapter):
    """In-memory adapter using one collection per record kind.

    Mirrors the storage layout used by MongoDB and the file adapter:
    each record kind (agent_update, outcome, trace, ...) is stored in
    its own dict, enabling efficient kind-scoped queries via listen().
    """

    def __init__(self) -> None:
        """Initialise an empty in-memory store."""
        self._collections: Dict[str, Dict[str, SimpleRecord]] = {}
        self._insertion_order: list[str] = []
        self._id_to_kind: Dict[str, str] = {}
        self._state_index: Dict[str, str] = {}

    def write(self, record: SimpleRecord) -> None:
        """Store a record in its kind's collection."""
        kind = record.kind
        if kind not in self._collections:
            self._collections[kind] = {}
        self._collections[kind][record.id] = record
        self._insertion_order.append(record.id)
        self._id_to_kind[record.id] = kind

    def read(self, record_id: str) -> Optional[SimpleRecord]:
        """Return a record by id if present."""
        kind = self._id_to_kind.get(record_id)
        if kind is None:
            return None
        return self._collections.get(kind, {}).get(record_id)

    def list(self) -> Iterable[SimpleRecord]:
        """Return records in insertion order."""
        results: list[SimpleRecord] = []
        for rid in self._insertion_order:
            kind = self._id_to_kind.get(rid)
            if kind is not None:
                record = self._collections[kind].get(rid)
                if record is not None:
                    results.append(record)
        return results

    def listen(
        self,
        kind: str,
        *,
        actor: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> Iterable[SimpleRecord]:
        """Yield records matching a kind with optional filters."""
        collection = self._collections.get(kind, {})
        records = list(collection.values())

        if actor is not None:
            records = [r for r in records if r.actor == actor]

        if since is not None:
            records = [r for r in records if r.timestamp >= since]

        if until is not None:
            records = [r for r in records if r.timestamp <= until]

        return records

    def lookup_outcome_by_hash(self, state_hash: str) -> Optional[str]:
        """Return outcome id for an already-seen state hash, or None."""
        return self._state_index.get(state_hash)

    def index_outcome(self, state_hash: str, outcome_id: str) -> None:
        """Store state_hash -> outcome_id mapping."""
        self._state_index[state_hash] = outcome_id

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
