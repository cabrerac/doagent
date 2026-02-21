"""Record envelope for shared data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from typing import TypedDict
except ImportError:  # pragma: no cover
    from typing_extensions import TypedDict


class Provenance(TypedDict, total=False):
    """Flat provenance attribution for a record.

    Answers "who created this record, from what inputs, using what tools?"
    One attribution per record (matches the design choice of one agent_update
    per agent per step). Records are immutable; provenance is set at write
    time. In a later iteration, one trace edge per ``derived_from`` source
    will be derived from provenance for graph traversal.
    """

    created_by: str
    derived_from: List[str]
    used_tools: List[str]
    notes: str


INITIAL_STATE_ID = "initial_state"
"""Fixed ID for the first environment outcome (state before any agent acts)."""


class Accountability(TypedDict, total=False):
    """Accountability metadata for a record.

    Ownership and governance context: who is responsible for this record,
    under which policy, and within what scope. Kept on the envelope so
    decisions can be reviewed, challenged, and governed without a separate
    record type. All fields are optional.
    """

    owner: str
    policy_id: str
    responsibility_scope: str


def new_provenance(
    *,
    agent: str,
    sources: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Build flat provenance attribution for use with new_record."""
    prov: Dict[str, Any] = {"created_by": agent}
    if sources:
        prov["derived_from"] = sources
    if tools:
        prov["used_tools"] = tools
    if notes is not None:
        prov["notes"] = notes
    return prov


def new_accountability(
    *,
    owner: Optional[str] = None,
    policy_id: Optional[str] = None,
    responsibility_scope: Optional[str] = None,
) -> Dict[str, Any]:
    """Build accountability dict for use with new_record."""
    out: Dict[str, Any] = {}
    if owner is not None:
        out["owner"] = owner
    if policy_id is not None:
        out["policy_id"] = policy_id
    if responsibility_scope is not None:
        out["responsibility_scope"] = responsibility_scope
    return out


class DecisionRequest(TypedDict, total=False):
    """Decision request payload for a model-agnostic agent."""

    id: str
    actor: str
    goal: str
    context: Dict[str, Any]
    inputs: Dict[str, Any]


class DecisionResponse(TypedDict, total=False):
    """Decision response payload for a model-agnostic agent."""

    id: str
    request_id: str
    actor: str
    decision: Dict[str, Any]
    notes: Optional[str]


class ExplanationPayload(TypedDict, total=False):
    """Human-readable explanation payload linked to a decision."""

    decision_id: str
    summary: str
    details: Optional[str]
    evidence: List[str]


class TracePayload(TypedDict, total=False):
    """Trace payload linking environment outcomes via agent_update transitions."""

    from_id: str
    to_id: str
    enabled_by_id: str
    relation: str
    round: Optional[int]
    actor: Optional[str]
    timestamp: Optional[str]
    notes: Optional[str]


@dataclass(frozen=True)
class SimpleRecord:
    """Shared data record envelope."""

    id: str
    timestamp: str
    actor: str
    kind: str
    payload: Dict[str, Any]
    provenance: Provenance = field(default_factory=dict)
    accountability: Accountability = field(default_factory=dict)


@dataclass(frozen=True)
class ExplanationRecord(SimpleRecord):
    """Explanation record envelope with `ExplanationPayload` in payload."""
