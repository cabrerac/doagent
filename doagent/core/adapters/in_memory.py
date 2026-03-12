"""In-memory shared data adapter: one collection per record kind."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from ...interface.shared_data import SharedDataAdapter
from ...records import SimpleRecord


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
