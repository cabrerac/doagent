"""In-memory participation registry."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

from .record import ParticipationRecord
from .registry import ParticipationRegistry


class InMemoryParticipationRegistry(ParticipationRegistry):
    """Simple in-memory registry for participation records."""

    def __init__(self) -> None:
        self._records: Dict[str, ParticipationRecord] = {}

    def register(self, record: ParticipationRecord) -> None:
        self._records[record.agent_id] = record

    def update(self, record: ParticipationRecord) -> None:
        self._records[record.agent_id] = record

    def deregister(self, agent_id: str) -> None:
        self._records.pop(agent_id, None)

    def get(self, agent_id: str) -> Optional[ParticipationRecord]:
        return self._records.get(agent_id)

    def list(self) -> Iterable[ParticipationRecord]:
        return list(self._records.values())
