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

## 3. Records Are Internal

**Users never call low-level record APIs directly.**

Functions such as `new_record()`, `new_agent_update_record()`, `new_trace_record()`, and `new_explanation_record()` are library-internal. They are used by validation scenarios, reporters, and orchestration layers—not by user code.

**User-facing API:**
- Agent objects (e.g. `FunctionAgent`) that the user calls in their run loop
- Env interface for stepping and observations
- Shared-data adapter selection (`InMemorySharedData`, `FileSharedData`)
- Configuration (logging level, run parameters)
- Optional convenience run APIs (e.g. `run_push_validation`) for canned scenarios

**Rationale:** Record shape, provenance, accountability, and trace linkage are implementation details. Exposing them would couple users to internal changes. The library applies them consistently and transparently.

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

- Shared data interface and adapters (in-memory, file-based)
- Record envelope and data model (see [data-model-spec.md](data-model-spec.md))
- Agent adapters (FunctionAgent, StubAgent)
- Validation scenarios (push, gridworld)
- Coordination hooks (topology, participation)
- Logging levels and configurable record writing

### Explicitly out of scope (for now)

- Distributed orchestration
- Network transport
- Storage backends beyond in-memory and file
- Agent discovery services
- Governance policy engines
- Deployment tooling

### Optional layers (post–core)

- Additional adapters (e.g. Mongo, SQL) provided by the library
- Orchestration and federation
- Admission and control plane
- Resource management
- Additional validation suites

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

- **Adapters:** Not extensible. The library provides a fixed set of adapters (e.g. `InMemorySharedData`, `FileSharedData`). Users select one; they cannot implement or add adapters.
- **Agents and policies:** Extensible. Users provide agent logic (callables, policies) and can define custom agents. The user invokes agents in their run loop; when called, agent objects return decisions and the library handles record writing internally.

---

## 13. Implications for Implementation

1. **Config object:** Run APIs and agent/scenario setup accept a config (e.g. `RunConfig`) that includes `logging_level`, agent IDs, and adapter. Record-writing code reads from it.
2. **Record writing via hooks:** The library uses hooks (e.g. on_agent_decide, on_env_step, after_outcome) to write records when the user invokes agents or steps the environment. A built-in hook gates writes by logging level. Transparent for users.
3. **No user imports of record helpers:** `new_record`, `new_agent_update_record`, etc. may remain in public `doagent.core` for internal and unit-test use; user documentation and examples should not show direct use.
4. **Examples:** Feature examples may use low-level helpers for pedagogical purposes; validation and E2E examples use only high-level run APIs with config.
5. **Adapter contract:** User chooses adapter; library assumes the adapter implements the shared data interface. Adapter handles concurrency in multi-process setups.
6. **Config validation:** Library validates config at run start; invalid config raises before any writes.

---

## References

- [Data Model Specification](data-model-spec.md)
- CIP-0001: Library First Architecture
- CIP-0002: Shared Data Model as Agent Interface
- Backlog: 2026-01-23_library-boundaries
