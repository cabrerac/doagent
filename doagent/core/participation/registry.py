"""Registry interface for participation records."""

from __future__ import annotations

from typing import Iterable, Optional, Protocol

from .record import ParticipationRecord


class ParticipationRegistry(Protocol):
    """Protocol for participation registries."""

    def register(self, record: ParticipationRecord) -> None:
        """Register a new participant."""

    def update(self, record: ParticipationRecord) -> None:
        """Update an existing participant."""

    def deregister(self, agent_id: str) -> None:
        """Remove a participant by agent id."""

    def get(self, agent_id: str) -> Optional[ParticipationRecord]:
        """Fetch a participant by agent id."""

    def list(self) -> Iterable[ParticipationRecord]:
        """List all participants."""
