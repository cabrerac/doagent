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

**Users never call low-level record APIs directly.**

Functions such as `new_record()`, `new_agent_update_record()`, `new_trace_record()`, and `new_explanation_record()` are library-internal. They are used by `RecordWriter`, `SessionAgent`, and `WrappedEnv`—not by user code.

**User-facing API (the Session layer):**

| What | User does | Library does internally |
|------|-----------|----------------------|
| `Session(shared_data, run_config, ...)` | Create once with adapter, config, topology | Wire `RecordWriter`, dedup, topology filtering |
| `session.wrap_env(env)` → `WrappedEnv` | Call `env.reset()` and `env.step(actions)` | Record `environment_outcome` + traces on each step |
| `session.create_agents(configs, registry)` → `SessionAgent` | Call `agent.decide(obs, round)` | Record `agent_update` on each decide |
| `session.visible_records(agent_id)` | Query shared data filtered by topology | Apply topology rules (centralised/P2P/federated) |
| `session.record_decision(...)` | Record external decisions (e.g. multiprocessing) | Write `agent_update` via `RecordWriter` |
| `session.record_update(...)` | Record non-decision updates (e.g. hub summaries) | Write `agent_update` via `RecordWriter` |

**Adapter selection:**
- `InMemorySharedData` — single-run, in-process
- `FileSharedData(directory)` — persistent, one JSONL file per record kind
- `MongoSharedData(db)` — MongoDB, one collection per record kind
- Custom adapters — implement the `SharedDataAdapter` protocol

**Configuration:**
- `RunConfig(logging_level=N)` — controls what gets recorded (§7)
- `TopologyConfig(mode=...)` — decentralisation mode (centralised/P2P/federated)
- `state_hash_fn` — controls state deduplication (on by default)

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

- **Session API** — central entry point for transparent recording, topology, dedup
- **Shared data interface and adapters** — `InMemorySharedData`, `FileSharedData`, `MongoSharedData`; `SharedDataAdapter` protocol for custom adapters
- **Record envelope and data model** — see [data-model-spec.md](data-model-spec.md)
- **State deduplication** — on by default (`default_state_hash` hashes state-category fields); scenario-overridable
- **Agent adapters** — `SessionAgent` (via Session), `FunctionAgent`, `StubAgent`
- **Validation scenarios** — push, gridworld (canonical usage examples live in `examples/validation/`; the validation *package* is internal to the research project — see [Architecture layers](architecture-layers.md))
- **Coordination** — topology (centralised/P2P/federated), participation registry, `visible_records()`
- **Logging levels** — configurable record writing gated by level (0, 1, 2)
- **Adapter contract** — documented interface with collection-per-kind storage model; see [adapter-contract.md](adapter-contract.md)

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

| Test type | Allowed API |
|-----------|-------------|
| **Unit tests** | May use internal record helpers (`new_record`, `new_agent_update_record`, etc.) to test logic in isolation. |
| **End-to-end tests** | Go through high-level run APIs only; assert on observable outputs and shared data state. |

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
- **Agents and policies:** Extensible. Users provide agent logic (callables, policies via `PolicyRegistry`) and can define custom agents. The user invokes agents in their run loop; when called, agent objects return decisions and the library handles record writing internally.
- **State deduplication:** Extensible. Users can replace the default hash function by passing a custom `state_hash_fn` to `Session`, or disable dedup entirely by passing `state_hash_fn=None`.
- **Topology:** Extensible via `TopologyConfig`. Users configure decentralisation mode at `Session` creation; the library enforces visibility rules through `session.visible_records()`.

---

## 13. Implications for Implementation

1. **Session is the wiring layer:** `Session` receives adapter, `RunConfig`, `TopologyConfig`, and `state_hash_fn`. It constructs `RecordWriter` internally and exposes `wrap_env()`, `create_agents()`, and `visible_records()` to the user.
2. **RecordWriter orchestrates writes:** `RecordWriter` gates writes by logging level, applies dedup (if hash fn is set), and delegates to the adapter. Users never interact with it directly.
3. **No user imports of record helpers:** `new_record`, `new_agent_update_record`, etc. remain in `doagent.core` for internal and unit-test use; user documentation and examples use only the Session layer.
4. **Adapters implement the Protocol:** Any object satisfying `SharedDataAdapter` works. The library ships three (`InMemorySharedData`, `FileSharedData`, `MongoSharedData`); users can add their own. The adapter contract is documented in [adapter-contract.md](adapter-contract.md).
5. **Collection-per-kind storage:** All adapters store records in separate logical collections by `kind` (e.g. `environment_outcome`, `agent_update`, `trace`). This enables efficient per-kind queries and aligns in-memory, file, and database backends.
6. **State deduplication is transparent:** `Session` defaults to `default_state_hash` (hashes `observations` + `done` fields). The user can override or disable. Dedup reuses existing outcome IDs and records pointer traces instead of duplicate outcomes.
7. **Topology is enforced by Session:** `visible_records()` applies topology rules, so agents only see records permitted by the configured mode.
8. **Config validation:** Library validates config at Session creation; invalid config raises before any writes.
9. **Examples:** Validation examples (push, gridworld) use only the Session API; feature examples may use low-level helpers for pedagogical purposes.

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
