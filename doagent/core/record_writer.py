"""Record writer with hook points for level-gated record creation.

Scenarios call RecordWriter hooks instead of new_record/new_agent_update_record
directly. RecordWriter encapsulates all record creation and writing.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from ..interface.shared_data import SharedDataAdapter
from ..records import SimpleRecord, new_accountability, new_provenance
from .run_config import (
    RunConfig,
    should_include_explanation,
    should_include_provenance_accountability,
    should_write_trace,
)
from .shared_data import new_agent_update_record, new_record, new_trace_record


def _serializable(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
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
    ) -> None:
        """Initialise with shared data and run config.

        Args:
            shared_data: Target for outcome and trace records.
            run_config: Logging level and other config.
            agent_write_fn: Optional. If provided, used for agent_update records
                (e.g. mp_interface.write_record). Else shared_data.write.
        """
        self._shared_data = shared_data
        self._config = run_config
        self._agent_write = agent_write_fn or shared_data.write

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
        provenance = new_provenance(agent=agent_id, sources=[]) if should_include_provenance_accountability(level) else {}
        accountability = new_accountability(owner=agent_id) if should_include_provenance_accountability(level) else {}
        record = new_agent_update_record(
            actor=agent_id,
            local_knowledge=local_knowledge,
            decision=decision,
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
        agent_update_ids: Dict[str, str],
        prev_outcome_id: str,
        env_actor: str,
        agent_ids: list[str],
    ) -> str:
        """Record environment outcome and optionally traces. Returns outcome record id."""
        level = self._config.logging_level
        payload = {
            "round": round_id,
            "actions": _serializable(actions),
            "rewards": _serializable(rewards),
            "observations": _serializable(observations),
        }
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
                    to_id=outcome_record.id,
                    enabled_by_id=agent_update_id,
                    relation="enables",
                    round_=round_id,
                    notes=f"Round {round_id} decision influenced outcome.",
                    provenance=trace_provenance,
                    accountability=trace_accountability,
                )
                self._shared_data.write(trace)

        return outcome_record.id
