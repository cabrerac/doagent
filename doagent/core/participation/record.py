"""Participation record definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ParticipationRecord:
    """Participation record for open agent discovery."""

    agent_id: str
    capabilities: List[str] = field(default_factory=list)
    resource_limits: Dict[str, float] = field(default_factory=dict)
    metadata: Optional[Dict[str, str]] = None
