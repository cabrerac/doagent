"""Agent adapter implementation."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from ..interface.agent_adapter import AgentAdapter
from ..interface.shared_data import SharedDataAdapter
from ..records import SimpleRecord
from .shared_data import new_record


class StubAgent:
    """Minimal agent adapter for validation."""

    def __init__(self, name: str, shared_data: SharedDataAdapter) -> None:
        """Initialise the adapter with a name and shared data backend."""
        self._name = name
        self._shared_data = shared_data

    def write(self, kind: str, payload: Dict[str, Any]) -> SimpleRecord:
        """Write a record to shared data."""
        record = new_record(actor=self._name, kind=kind, payload=payload)
        self._shared_data.write(record)
        return record

    def read(self, record_id: str) -> Optional[SimpleRecord]:
        """Read a record by id from shared data."""
        return self._shared_data.read(record_id)

    def listen(
        self,
        kind: str,
        *,
        actor: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> Iterable[SimpleRecord]:
        """Listen for records of a specific kind with optional filters."""
        return self._shared_data.listen(kind, actor=actor, since=since, until=until)
