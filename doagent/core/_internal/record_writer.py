"""Writes the records a session stores for a run.

What is stored follows the logging level.
Observation records are written at every level, because agents read them.
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
from .record_helpers import (
    new_agent_update_record,
    new_participation_record,
    new_record,
    new_trace_record,
)


StateHashFn = Callable[[Dict[str, Any]], str]
"""Callable: outcome payload -> hex digest string."""


_STATE_FIELDS = ("observations", "done")
"""Payload keys that represent environment state (not transition or temporal)."""


_HIDDEN_IN_MESSAGE = {
    "reasoning",
    "explanation",
    "inputs",
    "request",
    "local_knowledge",
    "observation",
    "response",
}
"""Keys that stay on the private decision and are dropped from a message."""


def default_state_hash(payload: Dict[str, Any]) -> str:
    """Return a SHA-256 digest of the state fields in an outcome.

    The digest covers observations and done.
    Actions, rewards, and the round are left out, so the same state at another round matches.

    Args:
        payload: Outcome content.

    Returns:
        The digest as hex text.
    """
    state = {k: payload[k] for k in _STATE_FIELDS if k in payload}
    canonical = json.dumps(state, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _message_payload(message: Any, round_id: Optional[int]) -> Dict[str, Any]:
    """Return the public content of a message.

    Reasoning and the decision input are left out.
    """
    if isinstance(message, dict):
        payload = {
            key: _serializable(value)
            for key, value in message.items()
            if key not in _HIDDEN_IN_MESSAGE
        }
    else:
        payload = {"text": _serializable(message)}
    if round_id is not None:
        payload["round"] = round_id
    return payload


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
    """Writes the records for one run.

    Which extra fields are stored depends on the logging level.
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
            agent_write_fn: Optional.
                If provided, used for agent_update records, such as mp_interface.write_record.
                Otherwise shared_data.write is used.
            state_hash_fn: Optional.
                If provided, enables state deduplication for environment outcomes.
                Receives the outcome payload dict and must return a hex digest string.
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
        sources: Optional[list[str]] = None,
        audience: Optional[list[str]] = None,
        message: Any = None,
        recipients: Optional[list[str]] = None,
        round_id: Optional[int] = None,
    ) -> str:
        """Record one agent decision, and a message when one is provided.

        The source list is written by the caller of this method.
        A policy response cannot set it.
        The message holds only the public content.

        Args:
            agent_id: Id of the agent that decided.
            local_knowledge: What the agent held locally for this decision.
            decision: The request and the response.
            response: Optional extra fields from the policy, such as an explanation.
            payload_type: Optional label stored with the decision.
            sources: Ids of the records shown for this decision.
                Omit it to store no source list.
            audience: Ids of the agents allowed to read the decision.
                Omit it to place no extra limit on readers.
            message: Public content for other agents.
                Omit it to write no message record.
            recipients: Ids of the agents allowed to read the message.
                Omit it to place no extra limit on readers who may see the author.
            round_id: Round number stored on the message.

        Returns:
            The id of the stored decision.

        Raises:
            TypeError: If recipients is a single string.
        """
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
        if should_include_provenance_accountability(level):
            provenance = new_provenance(agent=agent_id)
            if sources is not None:
                provenance["derived_from"] = list(sources)
        else:
            provenance = {}
        accountability = new_accountability(owner=agent_id) if should_include_provenance_accountability(level) else {}
        record = new_agent_update_record(
            actor=agent_id,
            local_knowledge=_serializable(local_knowledge),
            decision=_serializable(decision),
            payload_type=payload_type,
            provenance=provenance,
            accountability=accountability,
            audience=list(audience or []),
        )
        self._agent_write(record)
        if message is not None:
            self._write_message(
                agent_id=agent_id,
                message=message,
                recipients=recipients,
                round_id=round_id,
                decision_id=record.id,
                level=level,
                accountability=accountability,
            )
        return record.id

    def _write_message(
        self,
        *,
        agent_id: str,
        message: Any,
        recipients: Optional[list[str]],
        round_id: Optional[int],
        decision_id: str,
        level: int,
        accountability: Dict[str, Any],
    ) -> None:
        """Store the public message for one decision."""
        if isinstance(recipients, str):
            raise TypeError("recipients must be a list of agent ids, not a single string")
        provenance = (
            new_provenance(agent=agent_id, sources=[decision_id])
            if should_include_provenance_accountability(level)
            else {}
        )
        record = new_record(
            actor=agent_id,
            kind="message",
            payload=_message_payload(message, round_id),
            provenance=provenance,
            accountability=accountability,
            audience=list(recipients or []),
        )
        self._agent_write(record)

    def on_participation(
        self,
        *,
        agent_id: str,
        event: str,
        capabilities: Optional[list[str]] = None,
        resource_limits: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, str]] = None,
        members: Optional[list] = None,
        member_id: Optional[str] = None,
    ) -> str:
        """Record a participation event.

        The event is written at every logging level.
        Provenance and accountability are included from logging level 1 upward.

        Returns:
            The id of the stored record.
        """
        level = self._config.logging_level
        provenance = (
            new_provenance(agent=agent_id, sources=[])
            if should_include_provenance_accountability(level)
            else {}
        )
        accountability = (
            new_accountability(owner=agent_id)
            if should_include_provenance_accountability(level)
            else {}
        )
        record = new_participation_record(
            actor=agent_id,
            event=event,
            capabilities=capabilities,
            resource_limits=resource_limits,
            metadata=metadata,
            members=members,
            member_id=member_id,
            provenance=provenance,
            accountability=accountability,
        )
        self._shared_data.write(record)
        return record.id

    def on_addressed_observations(
        self,
        *,
        observations: Any,
        round_id: int,
        env_actor: str,
    ) -> list[str]:
        """Write one observation record per agent.

        The environment is the author.
        Each record is addressed to one agent.
        Only a dict of agent id to observation is split.
        Anything else writes nothing.
        The records are written at every logging level.

        Args:
            observations: Agent id to that agent's observation.
            round_id: Round these observations belong to.
                Reset uses 0.
            env_actor: Id of the environment that writes the records.

        Returns:
            The ids of the records written, in dict order.
        """
        if not isinstance(observations, dict):
            return []
        level = self._config.logging_level
        provenance = (
            new_provenance(agent=env_actor, sources=[])
            if should_include_provenance_accountability(level)
            else {}
        )
        accountability = (
            new_accountability(owner=env_actor)
            if should_include_provenance_accountability(level)
            else {}
        )
        record_ids: list[str] = []
        for agent_id, observation in observations.items():
            record = new_record(
                actor=env_actor,
                kind="observation",
                payload={
                    "round": round_id,
                    "observation": _serializable(observation),
                },
                provenance=provenance,
                accountability=accountability,
                audience=[str(agent_id)],
            )
            self._shared_data.write(record)
            record_ids.append(record.id)
        return record_ids

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
        """Record the combined environment outcome, and traces when the level allows it.

        The combined outcome still holds every agent's observation.
        Per-agent observation records are written separately.

        Returns:
            The id of the outcome record.
        """
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
        """Return an existing outcome id when the state was seen, otherwise write one.

        Args:
            payload: Outcome content.
            env_actor: Id of the environment that writes the outcome.
            agent_update_ids: Decision record id for each agent that acted.
            level: Logging level for this run.

        Returns:
            The id of the existing or new outcome record.
        """
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
            audience=[env_actor],
        )
        self._shared_data.write(outcome_record)

        if self._state_hash_fn is not None:
            state_hash = self._state_hash_fn(payload)
            indexer = getattr(self._shared_data, "index_outcome", None)
            if callable(indexer):
                indexer(state_hash, outcome_record.id)

        return outcome_record.id
