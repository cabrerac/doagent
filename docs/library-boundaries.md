# DOAgent Library Boundaries

This document defines the boundaries between user responsibilities and library responsibilities. It guides how the library is used, configured, and extended.

---

## 1. DOA Principles (Library Responsibilities)

The library embodies Data-Oriented Agent (DOA) principles. Alongside the **shared-data model**, two additional principles shape its design:

| Principle | Library responsibility |
|-----------|------------------------|
| **Shared-data model** | Records, adapters, trace, deduplication—users configure storage; library executes writes. |
| **Decentralisation** | Agents interact through shared data; no central orchestrator required. Library supports peer-to-peer coordination. |
| **Openness** | Interfaces and contracts are documented. Agents and their policies are extensible. |

As with all DOA principles: **users configure and control the run; the library executes record writes and config application internally and with transparency.** Behaviour is documented and predictable; implementation details stay internal.

---

## 2. User vs Library Responsibilities

| Who | Responsibility |
|-----|----------------|
| **User** | Owns the run: defines how runs execute, advances the environment, invokes agents. Provides environment, agent logic (policies), chooses shared-data adapter, sets run configuration once (e.g. logging level). |
| **Library** | Provides agent objects, env interfaces, and shared-data adapters. When the user invokes agents or steps the environment, the library writes records (based on config), handles read/write through the adapter, wires provenance and accountability. |

The user controls **when** things happen. The library handles **how** records are created, stored, and attributed—transparently, when the user’s run does something.

---

## 3. Records Are Internal — Session Is the API

**Supported public surface:** The library exposes only **`Session`**, **`RunConfig`**, and **`make_env`** from the top-level package (`from doagent import Session, RunConfig, make_env`). Tests, demos, and experiments use this surface only; they do not import adapters, `PolicyRegistry`, or other internals from `doagent.core`.

**Users never call low-level record APIs directly.**

Functions such as `new_record()`, `new_agent_update_record()`, `new_trace_record()`, and `new_explanation_record()` are library-internal. They are used by `RecordWriter`, `SessionAgent`, and `WrappedEnv`—not by user code.

**User-facing API (the Session layer):**

| What | User does | Library does internally |
|------|-----------|----------------------|
| `Session.from_config(config)` | Create session from a single config dict (shared_data type, policies, topology, run_config, optional `state_hash_fn`) | Build adapter, run config, topology; wire `RecordWriter`, dedup |
| `session.wrap_env(env)` → `WrappedEnv` | Call `env.reset()` and `env.step(actions)` | Record `environment_outcome` + traces on each step |
| `session.create_agents(configs)` → `SessionAgent` | Call `agent.decide(obs, round)` | Record `agent_update` on each decide (policies come from config) |
| `session.visible_records(agent_id)` | Query shared data filtered by topology | Apply topology rules (centralised/P2P/federated) |
| `session.record_decision(...)` | Record external decisions (e.g. multiprocessing) | Write `agent_update` via `RecordWriter` |
| `session.record_update(...)` | Record non-decision updates (e.g. hub summaries) | Write `agent_update` via `RecordWriter` |
| `session.inspect(kind)` | Read records by kind for assertions / analysis | Return records from adapter (filtered by kind) |

**Adapter selection (via config):** In the config passed to `Session.from_config`, set `shared_data` to a dict such as `{"type": "memory"}`, `{"type": "file", "directory": "..."}`, or `{"type": "noop"}`. The library instantiates the corresponding adapter internally. Direct use of `InMemorySharedData`, `FileSharedData`, or `MongoSharedData` is for internal/unit tests only.

**Configuration (in config dict or RunConfig):**
- `run_config` / `RunConfig(logging_level=N)` — controls what gets recorded (§7)
- `topology` / `TopologyConfig(mode=...)` — decentralisation mode (centralised/P2P/federated)
- `state_hash_fn` (optional) — controls state deduplication; omit or set to default for normal dedup

**Rationale:** Record shape, provenance, accountability, and trace linkage are implementation details. Exposing them would couple users to internal changes. The library applies them consistently and transparently via the Session layer.

---

## 4. Configured Once, Applied Automatically

**Users configure once at run start; the library applies configuration throughout.**

| Configuration | Where set | How applied |
|---------------|-----------|-------------|
| Logging level (0, 1, 2) | Run config or validation entry point | Library gates which records and fields are written based on level. |
| Agent IDs | Run config or participation definition | Library uses them for provenance, accountability, trace; these are the only unique properties per agent. |
| Adapter | Passed to run API | Library uses it for all read/write. |
| Provenance, accountability | Derived from context or optional config | Library populates envelope fields at Level 2. |

**No manual gating:** Users do not check logging level or conditionally call record helpers. The library checks the level at each write path and applies the appropriate behaviour.

---

## 5. Transparency

**Users know what they configured and what gets stored, but do not manage writes.**

- Configuration is explicit: user sets `logging_level`, adapter, etc.
- Behaviour is documented: data model spec describes what each level stores.
- Implementation is opaque: user does not see or control individual record creation.

**Transparent means:** The mapping from config to behaviour is documented and predictable. The mechanism (which internal functions run) is not exposed.

---

## 6. Library Scope

### Core (in scope)

- **Public API** — only `Session`, `RunConfig`, and `make_env` are exposed from the top-level package. Users create sessions via `Session.from_config(config)`; they do not import adapters or record types.
- **Storage** — users select storage via config (`shared_data.type`: `"memory"`, `"file"`, or `"noop"`). Adapters (`InMemorySharedData`, `FileSharedData`, `MongoSharedData`) and the `SharedDataAdapter` protocol are internal; see [adapter-contract.md](adapter-contract.md) for extension.
- **Record envelope and data model** — internal; see [data-model-spec.md](data-model-spec.md).
- **State deduplication** — on by default; configurable via optional `state_hash_fn` in config.
- **Agent surface** — users get `SessionAgent` instances from `session.create_agents(configs)`; policies are supplied in config. `FunctionAgent`, `StubAgent` are internal helpers for tests.
- **Validation scenarios** — push, gridworld (demos in `examples/`; experiment runners in `experiments/` use only the public Session API — see [Architecture layers](architecture-layers.md)).
- **Coordination** — topology (centralised/P2P/federated) and `visible_records()`; configured via config, not direct imports.
- **Logging levels** — configurable record writing gated by level (0, 1, 2).

**Core package layout** (`doagent/core/`): The core package is organised so that the **top level** holds only what backs the end-user API: **session.py**, **run_config.py**, **adapters/** (storage backends), **topology/**, and **participation/**. Implementation used by Session lives under **`_internal/`** (record_writer, record_helpers, policy). Helpers used for testing and advanced scenarios live under **`_helpers/`** (agent_adapter/StubAgent, function_agent/FunctionAgent). Users do not import from `doagent.core`. See [core-layout.md](core-layout.md) for the full layout.

### Explicitly out of scope (for now)

- Distributed orchestration
- Network transport
- Agent discovery services
- Governance policy engines
- Deployment tooling

### Deferred (future iterations)

- SQL/Postgres adapter
- Stream adapter (Kafka, Redis)
- Orchestration and federation layers
- Admission and control plane
- Resource management
- Additional validation suites (self-adaptive systems, scientific discovery)

---

## 7. Data-Oriented Logging Levels

Logging levels control what the library stores. See [data-model-spec.md](data-model-spec.md) §8.

| Level | Purpose | User configures | Library applies |
|-------|---------|-----------------|-----------------|
| **0** | Communication | `logging_level=0` | Writes agent_update, outcome; no trace, no explanation, no provenance/accountability. |
| **1** | Traceability, interpretability | `logging_level=1` | Adds trace, decision.explanation. |
| **2** | Accountability, provenance | `logging_level=2` | Adds provenance and accountability on envelope. |

The user sets the level; the library gates all record writes accordingly.

---

## 8. Identity and Participants

**Agent IDs come from config** and are the only unique properties per agent. The user (or scenario) defines participant IDs at run start; the library uses them for provenance, accountability, and trace linkage.

---

## 9. Error Handling and Guarantees

| Error type | Behaviour |
|------------|-----------|
| **Library internal error** | Propagate to caller; no partial state left. |
| **Agent error** | Retry; on failure, store the error in the shared data model for observability. |
| **Invalid config** | Validate first, when possible; validation is a library responsibility. Fail fast at run start if config is invalid. |

**Guarantees:**

- **No partial writes:** A write either completes fully or not at all; no half-persisted records.
- **Config validated before run:** The library validates config before starting the run, when feasible.
- **Agent errors observable:** Agent failures are recorded (when applicable) so they can be inspected and retried.

**Not guaranteed:** Ordering across parallel agents is adapter-defined (see §11).

---

## 10. Testing Boundary

Tests, demos, and experiments that define or validate the library’s supported behaviour use **only the public API**: `Session`, `RunConfig`, `make_env`, `Session.from_config`, `session.wrap_env`, `session.create_agents`, `session.inspect`, etc. No `doagent.core` or `doagent.records` imports in those code paths.

| Test type | Allowed API |
|-----------|-------------|
| **Scenario / validation / integration tests** | Public API only: `Session.from_config`, session methods, `session.inspect` for assertions. |
| **Unit tests of internal components** | May use `doagent.core` (adapters, topology, record helpers, `PolicyRegistry`) or `doagent.records` to test those components in isolation. |
| **Demos and experiment runners** | Public API only; they take a `Session` and use `session.inspect` or configured storage for outputs. |

---

## 11. Run Lifecycle and Concurrency

**Run lifecycle:** The user owns it. The user defines how runs execute (rounds, order, termination), advances the environment, and invokes agents. The library is flexible to support multiple and heterogeneous scenarios—no fixed lifecycle imposed by the library. This matches how multi-agent frameworks typically work: the user writes the run loop.

**Concurrency:**

| Setup | Behaviour | How supported |
|-------|-----------|---------------|
| **Single-process** | One agent acting at a time (or round-robin). | User orchestrates rounds in their loop; user decides participation order. |
| **Multi-process / decentralised** | Agents operate in parallel. | Each process has its own user-run loop and library instance; they share an adapter (DB, stream, etc.). The **adapter** handles concurrent access, ordering, and consistency. The library writes records; the adapter provides the concurrency semantics. |

The library does not implement distributed locking or coordination. Parallel support relies on the adapter (e.g. database transactions, message-ordering guarantees).

---

## 12. Extensibility

- **Adapters:** Extensible via Protocol. The library ships three adapters (`InMemorySharedData`, `FileSharedData`, `MongoSharedData`), but users can implement their own by satisfying the `SharedDataAdapter` protocol (see [adapter-contract.md](adapter-contract.md)). The optional dedup extension methods (`lookup_outcome_by_hash`, `index_outcome`) have no-op defaults, so a minimal adapter need only implement `write`, `read`, `list`, and `listen`.
- **Agents and policies:** Extensible. Users provide agent logic via the config passed to `Session.from_config` (e.g. `"policies": {"fixed": my_callable}`). The user invokes agents in their run loop; when called, agent objects return decisions and the library handles record writing internally.
- **State deduplication:** Extensible. Users can pass a custom `state_hash_fn` in the config to `Session.from_config`, or disable dedup by setting `state_hash_fn` to `None`.
- **Topology:** Extensible via config. Users set topology mode (and optional hub_id) in the config passed to `Session.from_config`; the library enforces visibility rules through `session.visible_records()`.

---

## 13. Implications for Implementation

1. **Session is the wiring layer:** User creates a session via `Session.from_config(config)`; the config carries `shared_data`, `run_config`, `topology`, `policies`, and optional `state_hash_fn`. Session constructs the adapter and `RecordWriter` internally and exposes `wrap_env()`, `create_agents()`, `visible_records()`, and `inspect()` to the user.
2. **RecordWriter orchestrates writes:** `RecordWriter` gates writes by logging level, applies dedup (if hash fn is set), and delegates to the adapter. Users never interact with it directly.
3. **No user imports of record helpers:** `new_record`, `new_agent_update_record`, etc. remain in `doagent.core` for internal and unit-test use; user documentation and examples use only the Session layer.
4. **Adapters implement the Protocol:** Any object satisfying `SharedDataAdapter` works. The library ships three (`InMemorySharedData`, `FileSharedData`, `MongoSharedData`); users can add their own. The adapter contract is documented in [adapter-contract.md](adapter-contract.md).
5. **Collection-per-kind storage:** All adapters store records in separate logical collections by `kind` (e.g. `environment_outcome`, `agent_update`, `trace`). This enables efficient per-kind queries and aligns in-memory, file, and database backends.
6. **State deduplication is transparent:** `Session` defaults to `default_state_hash` (hashes `observations` + `done` fields). The user can override or disable. Dedup reuses existing outcome IDs and records pointer traces instead of duplicate outcomes.
7. **Topology is enforced by Session:** `visible_records()` applies topology rules, so agents only see records permitted by the configured mode.
8. **Config validation:** Library validates config at Session creation; invalid config raises before any writes.
9. **Examples:** Demos (push_demo, gridworld_demo) use only the Session API; minimal_usage demonstrates config-driven setup.

---

## 14. Design Alternatives Considered

| Decision | Chosen | Alternative rejected | Reason |
|----------|--------|---------------------|--------|
| Adapters extensible | Protocol-based extensibility | Fixed set, no custom adapters | Users need domain-specific backends; Protocol makes this zero-cost |
| Session as entry point | Single `Session(...)` object | Users wire RecordWriter/agents manually | Wiring is error-prone (integration bugs found in practice) |
| Dedup on by default | `default_state_hash` active | Opt-in dedup | Trace graph is core to the data model; off-by-default would mean most users get flat logs |
| Collection-per-kind | Separate stores per `kind` | Single flat store | Per-kind enables efficient queries, matches MongoDB/file semantics, simplifies `listen` |

---

## References

- [Architecture Layers](architecture-layers.md) — core library | analysis (user-facing) | validation/experiments (internal)
- [Data Model Specification](data-model-spec.md)
- [Adapter Contract](adapter-contract.md)
- CIP-0001: Library First Architecture
- CIP-0002: Shared Data Model as Agent Interface
- Backlog: 2026-01-23_library-boundaries
