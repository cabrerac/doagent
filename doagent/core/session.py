"""Session-based API for transparent DOAgent usage.

Users create a Session, wrap their env, create agents, and run their loop.
Recording happens internally — no RecordWriter, INITIAL_STATE_ID, or
record helpers visible to user code.

Supports all three DOA principles:
- Shared-data model: records, adapters, trace, deduplication.
- Decentralisation: topology-filtered record access via visible_records().
- Openness: documented interfaces, extensible agents/policies.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from ..interface.shared_data import SharedDataAdapter
from ..records import INITIAL_STATE_ID, DecisionRequest, SimpleRecord
from .record_writer import RecordWriter, StateHashFn, default_state_hash, _serializable
from .run_config import RunConfig
from .topology import Topology, TopologyConfig

_DEDUP_DEFAULT = object()
"""Sentinel to distinguish 'not provided' from explicit None (opt-out)."""


# ---------------------------------------------------------------------------
# Env adapter: extracts (observations, rewards, done) from step result
# ---------------------------------------------------------------------------

StepAdapter = Callable[[Any], Dict[str, Any]]
"""Callable: raw step result -> {"observations": ..., "rewards": ..., "done": ...}"""


def _auto_adapt_step_result(result: Any) -> Dict[str, Any]:
    """Try common env conventions to extract observations, rewards, done."""
    if isinstance(result, dict):
        if "observations" in result:
            return {
                "observations": result["observations"],
                "rewards": result.get("rewards", {}),
                "done": result.get("done", result.get("terminations", {})),
            }

    if hasattr(result, "observations") and hasattr(result, "rewards"):
        return {
            "observations": result.observations,
            "rewards": result.rewards,
            "done": getattr(result, "terminations", getattr(result, "done", {})),
        }

    if isinstance(result, tuple):
        if len(result) >= 3:
            return {
                "observations": result[0],
                "rewards": result[1],
                "done": result[2],
            }

    raise TypeError(
        f"Cannot auto-detect step result shape ({type(result).__name__}). "
        "Provide an adapter to session.wrap_env(): "
        "adapter=lambda result: {'observations': ..., 'rewards': ..., 'done': ...}"
    )


# ---------------------------------------------------------------------------
# Wrapped environment
# ---------------------------------------------------------------------------

class WrappedEnv:
    """Env wrapper that records outcomes and traces on step() transparently."""

    def __init__(
        self,
        env: Any,
        record_writer: RecordWriter,
        env_actor: str,
        adapter: Optional[StepAdapter] = None,
    ) -> None:
        self._env = env
        self._record_writer = record_writer
        self._env_actor = env_actor
        self._adapter = adapter or _auto_adapt_step_result
        self._prev_outcome_id: str = INITIAL_STATE_ID
        self._round_id: int = 0
        self._agent_update_ids: Dict[str, str] = {}

    def reset(self, **kwargs: Any) -> Dict[str, Any]:
        """Reset the underlying env. Returns observations dict."""
        self._prev_outcome_id = INITIAL_STATE_ID
        self._round_id = 0
        self._agent_update_ids = {}
        result = self._env.reset(**kwargs)
        if isinstance(result, tuple) and len(result) == 2:
            return dict(result[0])
        if isinstance(result, dict):
            return dict(result)
        return result

    def step(self, actions: Dict[str, Any]) -> Dict[str, Any]:
        """Step the env and record outcome + traces. Returns extracted step data."""
        self._round_id += 1
        raw_result = self._env.step(actions)
        extracted = self._adapter(raw_result)

        self._prev_outcome_id = self._record_writer.on_outcome_and_traces(
            round_id=self._round_id,
            actions=actions,
            rewards=extracted["rewards"],
            observations=extracted["observations"],
            done=extracted.get("done"),
            agent_update_ids=dict(self._agent_update_ids),
            prev_outcome_id=self._prev_outcome_id,
            env_actor=self._env_actor,
            agent_ids=list(self._agent_update_ids.keys()),
        )
        self._agent_update_ids = {}
        return extracted

    def render(self) -> None:
        render_fn = getattr(self._env, "render", None)
        if callable(render_fn):
            render_fn()

    @property
    def agents(self) -> list[str]:
        return list(getattr(self._env, "agents", []))

    def _register_agent_update(self, agent_id: str, record_id: str) -> None:
        """Called by SessionAgent after decide() to register the update id."""
        self._agent_update_ids[agent_id] = record_id


# ---------------------------------------------------------------------------
# Wrapped agent
# ---------------------------------------------------------------------------

class SessionAgent:
    """Agent wrapper that records decisions transparently on decide()."""

    def __init__(
        self,
        agent_id: str,
        policy: Callable[..., Dict[str, Any]],
        record_writer: RecordWriter,
        wrapped_env: WrappedEnv,
        *,
        goal: str = "default",
        payload_type: Optional[str] = None,
    ) -> None:
        self._agent_id = agent_id
        self._policy = policy
        self._record_writer = record_writer
        self._env = wrapped_env
        self._goal = goal
        self._payload_type = payload_type

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def decide(
        self,
        observation: Any,
        round_id: int,
        *,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Call policy with observation, record agent_update, return response.

        Args:
            observation: The env observation for this agent.
            round_id: Current round number.
            inputs: Optional structured inputs dict for the request. If
                provided, used as ``request["inputs"]`` directly (so you
                can pass ``{"observation": ..., "shared_map": ...}``).
                Defaults to ``{"observation": observation}``.
        """
        obs = _serializable(observation)
        request_inputs = _serializable(inputs) if inputs is not None else {"observation": obs}
        request: DecisionRequest = {
            "id": f"req-{self._agent_id}-{round_id}-{uuid4()}",
            "actor": self._agent_id,
            "goal": self._goal,
            "context": {"round": round_id},
            "inputs": request_inputs,
        }
        response = dict(self._policy(request))

        response_clean = {
            k: v for k, v in response.items()
            if k not in ("provenance", "accountability")
        }
        decision = {"request": dict(request), "response": response_clean}
        local_knowledge = request_inputs

        record_id = self._record_writer.on_agent_decide(
            agent_id=self._agent_id,
            local_knowledge=local_knowledge,
            decision=decision,
            response=response,
            payload_type=self._payload_type,
        )
        self._env._register_agent_update(self._agent_id, record_id)

        action = response.get("decision", {}).get("action")
        return {"action": action, "response": response}


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class Session:
    """DOAgent session -- configure once, run transparently.

    Config-driven usage (recommended)::

        session = Session.from_config({
            "shared_data": {"type": "memory"},
            "topology": {"mode": "centralised"},
            "policies": {
                "my_policy": "my_project.policies:create_my_policy",
            },
        })
        env = session.wrap_env(make_env(create_fn, width=10))
        agents = session.create_agents(agent_configs)

        observations = env.reset(seed=42)
        for round_id in range(1, rounds + 1):
            actions = {}
            for agent_id, agent in agents.items():
                result = agent.decide(observations[agent_id], round_id)
                actions[agent_id] = result["action"]
            step = env.step(actions)
            observations = step["observations"]

        outcomes = session.inspect("outcome")

    Programmatic usage::

        session = Session(shared_data, run_config)
        env = session.wrap_env(my_env)
        agents = session.create_agents(configs, registry)
    """

    def __init__(
        self,
        shared_data: SharedDataAdapter,
        run_config: RunConfig | None = None,
        *,
        topology: TopologyConfig | None = None,
        visibility: Optional[Dict[str, List[str]]] = None,
        hub_id: str = "hub",
        agent_write_fn: Optional[Callable[..., None]] = None,
        state_hash_fn: Any = _DEDUP_DEFAULT,
    ) -> None:
        self._shared_data = shared_data
        self._config = run_config or RunConfig()
        self._topology = topology or TopologyConfig()
        self._visibility = visibility or {}
        self._hub_id = hub_id
        resolved_hash_fn: Optional[StateHashFn] = (
            default_state_hash if state_hash_fn is _DEDUP_DEFAULT else state_hash_fn
        )
        self._record_writer = RecordWriter(
            shared_data,
            self._config,
            agent_write_fn=agent_write_fn,
            state_hash_fn=resolved_hash_fn,
        )
        self._wrapped_env: Optional[WrappedEnv] = None
        self._policy_registry: Optional[Any] = None

    @property
    def topology_mode(self) -> str:
        """Topology mode as a string (e.g. "centralised", "federated")."""
        return self._topology.mode.value

    @property
    def hub_id(self) -> str:
        """Hub agent identifier for federated topology."""
        return self._hub_id

    def inspect(self, kind: str) -> List[Any]:
        """Inspect records produced during the run, by kind.

        Provides transparent access to what the library recorded.
        Supports the transparency goal: users can inspect outcomes,
        traces, and agent decisions after a run.

        Args:
            kind: Record kind — "outcome", "trace", or "agent_update".

        Returns:
            List of records of that kind.

        Examples::

            outcomes = session.inspect("outcome")
            traces = session.inspect("trace")
            decisions = session.inspect("agent_update")
        """
        return list(self._shared_data.listen(kind))

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "Session":
        """Build a Session from a config dict. Keeps adapter construction internal.

        Config keys (all optional):
          - shared_data: {"type": "memory"|"file"|"noop"} (file requires "path")
          - run_config: {"logging_level": 0|1|2}
          - topology: {"mode": "centralised"|"peer_to_peer"|"federated", "visibility": {...}}
          - policies: {name: entry_point_or_callable, ...}
          - hub_id: str (default "hub")
        """
        from .file_shared_data import FileSharedData
        from .shared_data import InMemorySharedData

        sd_cfg = config.get("shared_data") or {}
        sd_type = (sd_cfg.get("type") or "memory").lower()
        if sd_type == "memory":
            shared_data: SharedDataAdapter = InMemorySharedData()
        elif sd_type == "file":
            path = sd_cfg.get("path")
            if not path:
                raise ValueError("shared_data.type 'file' requires shared_data.path")
            shared_data = FileSharedData(path)
        elif sd_type == "noop":
            from .noop_adapter import NoOpSharedData
            shared_data = NoOpSharedData()
        else:
            raise ValueError(f"shared_data.type must be 'memory', 'file', or 'noop'; got {sd_type!r}")

        rc_cfg = config.get("run_config") or {}
        level = rc_cfg.get("logging_level", 2)
        run_config = RunConfig(logging_level=level)

        topo_cfg = config.get("topology") or {}
        mode_str = (topo_cfg.get("mode") or "centralised").lower()
        try:
            mode = Topology(mode_str)
        except ValueError:
            mode = Topology("centralised")
        topology = TopologyConfig(mode=mode)
        visibility = topo_cfg.get("visibility") or None
        hub_id = config.get("hub_id", "hub")

        session = cls(
            shared_data,
            run_config,
            topology=topology,
            visibility=visibility,
            hub_id=hub_id,
        )

        policies_cfg = config.get("policies") or {}
        if policies_cfg:
            from ..env import _resolve_entry_point
            from .policy import PolicyRegistry

            registry = PolicyRegistry()
            for name, entry_point in policies_cfg.items():
                factory = _resolve_entry_point(entry_point)
                registry.register(name, factory)
            session._policy_registry = registry

        return session

    def wrap_env(
        self,
        env: Any,
        *,
        env_actor: str = "env",
        adapter: Optional[StepAdapter] = None,
    ) -> WrappedEnv:
        """Wrap a user environment for transparent recording."""
        self._wrapped_env = WrappedEnv(
            env, self._record_writer, env_actor, adapter=adapter,
        )
        return self._wrapped_env

    def create_agents(
        self,
        configs: list[Dict[str, Any]],
        registry: Any = None,
        *,
        goal: str = "default",
        payload_type: Optional[str] = None,
    ) -> Dict[str, SessionAgent]:
        """Create wrapped agents from configs and a PolicyRegistry.

        Each config is a dict with:
          - "id": str -- agent identifier
          - "policy": dict -- policy name and params (e.g. {"name": "my_policy", "params": {...}})
          - "metadata": dict, optional -- e.g. {"explanation": "..."} for interpretability

        If *registry* is None, the session's internal registry (built by
        ``from_config``) is used.  This lets config-driven setups work
        without the user ever importing ``PolicyRegistry``.
        """
        if self._wrapped_env is None:
            raise RuntimeError("Call session.wrap_env() before create_agents().")
        effective_registry = registry or self._policy_registry
        if effective_registry is None:
            raise RuntimeError(
                "No policy registry available. Pass one explicitly or "
                "include 'policies' in the config given to Session.from_config()."
            )
        agents: Dict[str, SessionAgent] = {}
        for config in configs:
            agent_id = config["id"]
            policy = effective_registry.create(config["policy"])
            metadata = config.get("metadata", {})
            if metadata:
                policy = _wrap_policy_with_metadata(policy, metadata)
            agents[agent_id] = SessionAgent(
                agent_id=agent_id,
                policy=policy,
                record_writer=self._record_writer,
                wrapped_env=self._wrapped_env,
                goal=goal,
                payload_type=payload_type,
            )
        return agents

    def record_decision(
        self,
        agent_id: str,
        observation: Any,
        response: Dict[str, Any],
        round_id: int,
        *,
        goal: str = "default",
        payload_type: Optional[str] = None,
    ) -> str:
        """Record a decision made externally (e.g. multiprocessing workers).

        Registers the agent_update on the wrapped env so the next env.step()
        includes it in outcome/trace records.
        """
        obs = _serializable(observation)
        request: Dict[str, Any] = {
            "id": f"req-{agent_id}-{round_id}-{uuid4()}",
            "actor": agent_id,
            "goal": goal,
            "context": {"round": round_id},
            "inputs": {"observation": obs},
        }
        response_clean = {
            k: v for k, v in response.items()
            if k not in ("provenance", "accountability")
        }
        decision = {"request": request, "response": response_clean}
        local_knowledge = {"observation": obs}

        record_id = self._record_writer.on_agent_decide(
            agent_id=agent_id,
            local_knowledge=local_knowledge,
            decision=decision,
            response=response,
            payload_type=payload_type,
        )
        if self._wrapped_env is not None:
            self._wrapped_env._register_agent_update(agent_id, record_id)
        return record_id

    def record_update(
        self,
        agent_id: str,
        local_knowledge: Dict[str, Any],
        *,
        payload_type: Optional[str] = None,
    ) -> str:
        """Record a non-decision update (e.g. hub summary in federated topology)."""
        record_id = self._record_writer.on_agent_decide(
            agent_id=agent_id,
            local_knowledge=local_knowledge,
            decision={},
            response={},
            payload_type=payload_type,
        )
        return record_id

    def visible_records(
        self,
        agent_id: str,
        kind: Optional[str] = None,
    ) -> List[SimpleRecord]:
        """Return records visible to *agent_id* under the configured topology.

        - CENTRALISED: all records of the given kind.
        - PEER_TO_PEER: only records from *agent_id* itself and its
          visible peers (as defined by the visibility map).
        - FEDERATED: only records authored by the hub. If *agent_id* is
          the hub itself, all records are returned (the hub aggregates).
        """
        all_records = list(self._shared_data.listen(kind))
        mode = self._topology.mode

        if mode == Topology.CENTRALISED:
            return all_records

        if mode == Topology.PEER_TO_PEER:
            allowed: set[str] = {agent_id}
            if agent_id in self._visibility:
                allowed.update(self._visibility[agent_id])
            return [r for r in all_records if r.actor in allowed]

        if mode == Topology.FEDERATED:
            if agent_id == self._hub_id:
                return all_records
            return [r for r in all_records if r.actor == self._hub_id]

        return all_records

    @property
    def shared_data(self) -> SharedDataAdapter:
        """Direct access to the shared data adapter (for advanced use)."""
        return self._shared_data

    @property
    def topology(self) -> TopologyConfig:
        """The configured topology."""
        return self._topology


def _wrap_policy_with_metadata(
    policy: Callable[..., Dict[str, Any]],
    metadata: Dict[str, Any],
) -> Callable[..., Dict[str, Any]]:
    """Inject explanation metadata into policy responses.

    Provenance and accountability are handled by RecordWriter at the
    appropriate logging level — not injected via metadata.
    """
    explanation = metadata.get("explanation")
    if explanation is None:
        return policy

    def wrapped(request: Any) -> Dict[str, Any]:
        response = dict(policy(request))
        if "explanation" not in response:
            response["explanation"] = explanation
        return response
    return wrapped
