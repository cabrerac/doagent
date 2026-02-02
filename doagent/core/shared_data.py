"""Shared data adapters and record helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional
from uuid import uuid4

from ..interface.shared_data import SharedDataAdapter
from ..records import SimpleRecord

class InMemorySharedData(SharedDataAdapter):
    """In-memory adapter for the shared data model."""

    def __init__(self) -> None:
        """Initialise an empty in-memory store."""
        self._records: Dict[str, SimpleRecord] = {}

    def write(self, record: SimpleRecord) -> None:
        """Store a record by its id."""
        self._records[record.id] = record

    def read(self, record_id: str) -> Optional[SimpleRecord]:
        """Return a record by id if present."""
        return self._records.get(record_id)

    def list(self) -> Iterable[SimpleRecord]:
        """Return records in insertion order."""
        return list(self._records.values())

    def listen(
        self,
        kind: str,
        *,
        actor: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> Iterable[SimpleRecord]:
        """Yield records matching a kind with optional filters."""
        records = [record for record in self._records.values() if record.kind == kind]

        if actor is not None:
            records = [record for record in records if record.actor == actor]

        if since is not None:
            records = [record for record in records if record.timestamp >= since]

        if until is not None:
            records = [record for record in records if record.timestamp <= until]

        return records

def new_record(
    *,
    actor: str,
    kind: str,
    payload: Dict[str, Any],
    provenance: Optional[Dict[str, Any]] = None,
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
    )
