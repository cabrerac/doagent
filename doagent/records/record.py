"""Record envelope for shared data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from typing import TypedDict
except ImportError:  # pragma: no cover
    from typing_extensions import TypedDict


class Contribution(TypedDict, total=False):
    """Contribution entry for a single agent and its sources/tools."""

    id: str
    agent: str
    sources: List[str]
    tools: List[str]
    notes: Optional[str]


class Provenance(TypedDict, total=False):
    """Provenance metadata for a record."""

    contributions: List[Contribution]


@dataclass(frozen=True)
class SimpleRecord:
    """Shared data record envelope."""

    id: str
    timestamp: str
    actor: str
    kind: str
    payload: Dict[str, Any]
    provenance: Provenance = field(default_factory=dict)
