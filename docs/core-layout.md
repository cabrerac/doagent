# Core package layout and file roles

This document describes the layout of `doagent/core/` and the role of each part. **Users do not import from `doagent.core`**; the public API is only `Session`, `RunConfig`, and `make_env` from the top-level `doagent` package. The top level of `core/` backs that API; the rest is under `_internal/` (used by Session) and `_helpers/` (used by unit tests and internal code).

---

## Top level (user-facing surface)

| Item | Purpose |
|------|---------|
| **session.py** | `Session`, `SessionAgent`, `WrappedEnv` — main API. |
| **run_config.py** | `RunConfig`, logging-level helpers. |
| **adapters/** | Storage backends: `InMemorySharedData`, `FileSharedData`, `MongoSharedData`, `NoOpSharedData`. |
| **topology/** | `Topology`, `TopologyConfig`, `RoutingDecision`, `select_routing`. |
| **participation/** | `ParticipationRecord`, `ParticipationRegistry`, `InMemoryParticipationRegistry`. |

Together these support the public API: `doagent.Session`, `doagent.RunConfig`, `doagent.make_env`. Adapters and other symbols are internal; users configure storage via `Session.from_config(config)` with `shared_data.type`.

---

## _internal/ (used by Session)

Implementation details used by Session; not part of the minimal public API. Still re-exported from `doagent.core` for tests and advanced use.

| File | Purpose |
|------|---------|
| **record_writer.py** | `RecordWriter`, `StateHashFn`, `default_state_hash` — writes outcome/trace/agent_update records. |
| **record_helpers.py** | `new_record`, `new_agent_update_record`, `new_trace_record`, `new_explanation_record` — record factory helpers. |
| **policy.py** | `PolicyRegistry`, `Policy`, `PolicyConfig` — used by `Session.from_config` to build agents from a policies dict. |

---

## _helpers/ (used for testing)

Helpers used in tests and custom setups; not required for the minimal Session + make_env + config flow.

| File | Purpose |
|------|---------|
| **agent_adapter.py** | `StubAgent` — minimal adapter for writing/reading records. |
| **function_agent.py** | `FunctionAgent` — decision agent backed by a callable. |

Session uses its own `SessionAgent`; `StubAgent` and `FunctionAgent` are for tests and advanced scenarios.

---

## “Power-user” meaning

**Power-user** here means: code (or a user) that goes beyond the minimal “import doagent, use Session and make_env” flow and imports from `doagent.core` directly — e.g. `PolicyRegistry`, `TopologyConfig`, `FunctionAgent`, `StubAgent`, or record helpers — for custom wiring, tests, or experiments. The supported user API is only `doagent.Session`, `doagent.RunConfig`, and `doagent.make_env`; users create sessions via `Session.from_config(config)` and do not import adapters or record types. Unit tests and internal code may import from `doagent.core`.

---

## Summary

- **Top level:** session, run_config, adapters, topology, participation.
- **_internal:** record_writer, record_helpers, policy (used by Session).
- **_helpers:** agent_adapter (StubAgent), function_agent (FunctionAgent) (used for testing).

All of the above are re-exported from `doagent.core` so existing `from doagent.core import ...` and `from doagent.core import PolicyRegistry` etc. continue to work.
