"""Shared data interfaces and record envelope."""

from __future__ import annotations

from typing import Iterable, Optional, Protocol


from ..records import SimpleRecord


class SharedDataAdapter(Protocol):
    """Protocol for shared data adapters."""

    def write(self, record: SimpleRecord) -> None:
        """Persist a record to the shared data model."""

    def read(self, record_id: str) -> Optional[SimpleRecord]:
        """Read a record by id."""

    def list(self) -> Iterable[SimpleRecord]:
        """List all records in adapter order."""

    def listen(
        self,
        kind: str,
        *,
        actor: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> Iterable[SimpleRecord]:
        """Yield records matching a kind with optional filters."""

    def lookup_outcome_by_hash(self, state_hash: str) -> Optional[str]:
        """Return the outcome record id for an already-seen state hash.

        Adapters that do not support deduplication should return ``None``.
        """
        return None

    def index_outcome(self, state_hash: str, outcome_id: str) -> None:
        """Store a ``state_hash -> outcome_id`` mapping for dedup lookups.

        Adapters that do not support deduplication may no-op.
        """
