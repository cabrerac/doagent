"""Record writer with hook points for level-gated record creation.

Scenarios call RecordWriter hooks instead of new_record/new_agent_update_record
directly. RecordWriter encapsulates all record creation and writing.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Dict, Optional

from ...interface.shared_data import SharedDataAdapter
from ...records import SimpleRecord, new_accountability, new_provenance
from ..run_config import (
    RunConfig,
    should_include_explanation,
    should_include_provenance_accountability,
    should_include_reasoning,
    should_write_trace,
)
from .record_helpers import new_agent_update_record, new_record, new_trace_record


StateHashFn = Callable[[Dict[str, Any]], str]
"""Callable: outcome payload -> hex digest string."""


_STATE_FIELDS = ("observations", "done")
"""Payload keys that represent environment state (not transition or temporal)."""


def default_state_hash(payload: Dict[str, Any]) -> str:
    """SHA-256 of state-only fields (observations, done).

    Excludes transition fields (actions, rewards) and temporal fields
    (round) so that revisiting the same physical state at different
    rounds correctly deduplicates.
    """
    state = {k: payload[k] for k in _STATE_FIELDS if k in payload}
    canonical = json.dumps(state, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _serializable(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if callable(value) and not isinstance(value, (bool, type)):
        return f"<callable:{getattr(value, '__name__', type(value).__name__)}>"
    if isinstance(value, dict):
        return {k: _serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serializable(item) for item in value]
    return value


class RecordWriter:
    """Writes records to shared data based on run config.

    Hook points: on_agent_decide, on_outcome_and_traces.
    Scenarios call these instead of new_* primitives.
    """

    def __init__(
        self,
        shared_data: SharedDataAdapter,
        run_config: RunConfig,
        *,
        agent_write_fn: Optional[Callable[[SimpleRecord], None]] = None,
        state_hash_fn: Optional[StateHashFn] = None,
    ) -> None:
        """Initialise with shared data and run config.

        Args:
            shared_data: Target for outcome and trace records.
            run_config: Logging level and other config.
            agent_write_fn: Optional. If provided, used for agent_update records
                (e.g. mp_interface.write_record). Else shared_data.write.
            state_hash_fn: Optional. If provided, enables state deduplication
                for environment outcomes. Receives the outcome payload dict and
                must return a hex digest string.
        """
        self._shared_data = shared_data
        self._config = run_config
        self._agent_write = agent_write_fn or shared_data.write
        self._state_hash_fn = state_hash_fn

    def on_agent_decide(
        self,
        *,
        agent_id: str,
        local_knowledge: Dict[str, Any],
        decision: Dict[str, Any],
        response: Optional[Dict[str, Any]] = None,
        payload_type: Optional[str] = None,
    ) -> str:
        """Record agent_update. Returns record id."""
        response = response or {}
        level = self._config.logging_level
        if should_include_explanation(level) and "explanation" in response:
            decision = dict(decision)
            decision["explanation"] = response["explanation"]
        if not should_include_reasoning(level) and "response" in decision:
            resp = decision.get("response")
            if isinstance(resp, dict) and "reasoning" in resp:
                decision = dict(decision)
                decision["response"] = {k: v for k, v in resp.items() if k != "reasoning"}
        provenance = new_provenance(agent=agent_id, sources=[]) if should_include_provenance_accountability(level) else {}
        accountability = new_accountability(owner=agent_id) if should_include_provenance_accountability(level) else {}
        record = new_agent_update_record(
            actor=agent_id,
            local_knowledge=_serializable(local_knowledge),
            decision=_serializable(decision),
            payload_type=payload_type,
            provenance=provenance,
            accountability=accountability,
        )
        self._agent_write(record)
        return record.id

    def on_outcome_and_traces(
        self,
        *,
        round_id: int,
        actions: Dict[str, Any],
        rewards: Dict[str, Any],
        observations: Dict[str, Any],
        done: Optional[Dict[str, Any]] = None,
        agent_update_ids: Dict[str, str],
        prev_outcome_id: str,
        env_actor: str,
        agent_ids: list[str],
    ) -> str:
        """Record environment outcome and optionally traces. Returns outcome record id."""
        level = self._config.logging_level
        payload: Dict[str, Any] = {
            "round": round_id,
            "actions": _serializable(actions),
            "rewards": _serializable(rewards),
            "observations": _serializable(observations),
        }
        if done is not None:
            payload["done"] = _serializable(done)

        outcome_id = self._dedup_or_write_outcome(payload, env_actor, agent_update_ids, level)

        if should_write_trace(level):
            for agent_id in agent_ids:
                agent_update_id = agent_update_ids.get(agent_id)
                if agent_update_id is None:
                    continue
                trace_provenance = (
                    new_provenance(agent=agent_id, sources=[agent_update_id])
                    if should_include_provenance_accountability(level)
                    else {}
                )
                trace_accountability = (
                    new_accountability(owner=agent_id) if should_include_provenance_accountability(level) else {}
                )
                trace = new_trace_record(
                    actor=agent_id,
                    from_id=prev_outcome_id,
                    to_id=outcome_id,
                    enabled_by_id=agent_update_id,
                    relation="enables",
                    round_=round_id,
                    notes=f"Round {round_id} decision influenced outcome.",
                    provenance=trace_provenance,
                    accountability=trace_accountability,
                )
                self._shared_data.write(trace)

        return outcome_id

    def _dedup_or_write_outcome(
        self,
        payload: Dict[str, Any],
        env_actor: str,
        agent_update_ids: Dict[str, str],
        level: int,
    ) -> str:
        """Check state index for dedup; write new outcome only when needed."""
        if self._state_hash_fn is not None:
            state_hash = self._state_hash_fn(payload)
            lookup = getattr(self._shared_data, "lookup_outcome_by_hash", None)
            if callable(lookup):
                existing_id = lookup(state_hash)
                if existing_id is not None:
                    return existing_id

        outcome_provenance = (
            new_provenance(
                agent=env_actor,
                sources=list(agent_update_ids.values()),
                tools=[env_actor],
            )
            if should_include_provenance_accountability(level)
            else {}
        )
        outcome_accountability = (
            new_accountability(owner=env_actor) if should_include_provenance_accountability(level) else {}
        )
        outcome_record = new_record(
            actor=env_actor,
            kind="outcome",
            payload=payload,
            provenance=outcome_provenance,
            accountability=outcome_accountability,
        )
        self._shared_data.write(outcome_record)

        if self._state_hash_fn is not None:
            state_hash = self._state_hash_fn(payload)
            indexer = getattr(self._shared_data, "index_outcome", None)
            if callable(indexer):
                indexer(state_hash, outcome_record.id)

        return outcome_record.id
