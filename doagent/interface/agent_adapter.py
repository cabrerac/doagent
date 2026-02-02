"""Agent adapter interface."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Protocol

from ..records import SimpleRecord


class AgentAdapter(Protocol):
    """Protocol for agent adapters."""

    def write(self, kind: str, payload: Dict[str, Any]) -> SimpleRecord:
        """Write an agent decision to shared data."""

    def read(self, record_id: str) -> Optional[SimpleRecord]:
        """Read a record from shared data."""

    def listen(
        self,
        kind: str,
        *,
        actor: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> Iterable[SimpleRecord]:
        """Listen for records of a specific kind with optional filters."""
