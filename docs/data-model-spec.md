# DOAgent Shared Data Model Specification

This document specifies the shared data model used for agent communication, coordination, traceability, and accountability. It serves as the reference for implementation (CIP-0002) and for data-oriented logging levels (REQ-0001 / CIP-0001).

---

## 1. Design Choices

| Choice | Decision | Rationale |
|--------|----------|-----------|
| **Structure** | Flat event log | Records are written one-by-one as events occur; grouping is a read/query concern. Supports streaming and adapter flexibility. |
| **Provenance & accountability** | Record envelope only | Single source of truth per record; no duplication inside payloads. |
| **Agent activity** | One agent_update per agent per step | Default design; provenance is a flat attribution (one creator per record). |
| **Initial state** | Fixed ID `"initial_state"` | First environment outcome before any agent acts; no UUID generation; stable reference. |

---

## 2. Record Envelope

All records share a common envelope:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | str | Yes | Unique record identifier |
| `timestamp` | str | Yes | ISO 8601 or equivalent |
| `actor` | str | Yes | Entity that produced the record (agent id, env id) |
| `kind` | str | Yes | Record kind (see below) |
| `payload` | dict | Yes | Kind-specific content |
| `provenance` | dict | No* | Authorship: who produced this record (see §6) |
| `accountability` | dict | No* | Responsibility: who answers for this record (see §6) |

\* At Level 2, provenance and accountability are populated on all records. At Levels 0 and 1, they may be omitted or minimal.

---

## 3. Record Kinds — Agent Side

### 3.1 agent_update

**Role:** The central agent entity—both the message agents exchange and the unit of agent activity. One per agent per step. Produced for every agent that acts (gridworld, push, etc.).

**Payload:**
- `local_knowledge` (required): What the agent knows at update time. Scenario-specific structure (e.g. gridworld cells, push observations). Temporal snapshot. May be empty for scenarios without agent-to-agent messaging.
- `decision` (required): The agent's choice. Contains:
  - `request`: Input to the decision (actor, goal, context, inputs)
  - `response`: Output (actor, decision, request_id, notes)
  - `explanation` (optional, by level): Human-readable rationale. Populated at Level 1+. Like provenance/accountability on the envelope, explanation is an optional attribute controlled by the logging level.
- `type`: Message type when applicable (e.g. `map_update`, `map_summary` for gridworld)
- Other scenario-defined fields

**Optional envelope fields (by level):** provenance, accountability at Level 2. No provenance or accountability inside the payload.

---

### 3.2 trace

**Role:** Links state transitions in the environment. Forms a directed graph of states and actions.

**Payload:**
- `from_id`: environment_outcome id (state before)
- `to_id`: environment_outcome id (state after)
- `enabled_by_id`: agent_update id that caused the transition
- `round`, `timestamp`: Temporal metadata (lives on trace, not on outcome)

**Note:** The first trace uses `from_id: "initial_state"`.

---

## 4. Record Kinds — Environment Side

### 4.1 environment_outcome

**Role:** The environment's response after an env step. Records the resulting state and transition context.

**Payload — recommended top-level keys:**

| Key | Type | Category | Description |
|-----|------|----------|-------------|
| `observations` | `Dict[str, Any]` | State | Per-agent observations after the step. This is the primary state content. |
| `done` | `Dict[str, bool]` | State | Per-agent termination flags. |
| `rewards` | `Dict[str, float]` | Transition | Per-agent reward values resulting from this transition. |
| `actions` | `Dict[str, Any]` | Transition | The joint action that caused this transition. |
| `round` | `int` | Temporal | Step index. Also present on traces for graph queries. |

**Payload is open key-value.** Scenarios may add domain-specific keys (e.g. `infos`, `truncations`, `grid_state`). The table above lists recommended common keys, not a rigid schema.

**Category semantics for deduplication:**
- **State** keys (`observations`, `done`) define what the environment "looks like" — these are the natural candidates for the `state_hash_fn`.
- **Transition** keys (`rewards`, `actions`) describe how we arrived — useful for analysis but typically excluded from the state hash.
- **Temporal** keys (`round`) index the step — always excluded from state hashes since the same state can be reached at different times.

### 4.2 reward, env_status

**Conceptual components** of environment_outcome, not separate record kinds. `rewards` and `done` are top-level keys in the outcome payload.

---

## 5. Relationships

```
agent_update  contains  local_knowledge, decision (decision contains optional explanation)
trace         ──→  from: env_outcome, to: env_outcome, enabled_by: agent_update
environment_outcome  contains  reward, env_status
```

**Trace graph:** Traces form a directed graph. Nodes = environment outcomes (states). Edges = traces with `enabled_by` agent_update. State deduplication: equivalent states (by hash) reuse the same outcome id; multiple traces can point to the same outcome.

---

## 6. Provenance vs Accountability

| Concept | Meaning |
|--------|---------|
| **Provenance** | Attribution. *Who created this record, from what inputs, using what tools?* |
| **Accountability** | Responsibility. *Who answers for this record?* Can differ from authorship (delegation, team ownership, policy). |

**Provenance schema (flat attribution):**

| Field | Type | Description |
|-------|------|-------------|
| `created_by` | `str` | Agent id that produced this record |
| `derived_from` | `List[str]` | Input record ids used to produce this record |
| `used_tools` | `List[str]` | Tool identifiers used during production |
| `notes` | `str` | Free-text annotation |

All fields are optional. Minimal provenance contains only `created_by`.

One attribution per record — matches the design choice of one `agent_update` per agent per step (§1). The previous `contributions: List[Contribution]` structure was removed because it implied collaborative multi-agent authorship of a single record, which does not match the actual write model.

**Accountability schema:** `owner`, `policy_id`, `responsibility_scope` (all optional).

---

## 7. Initial State

The first environment outcome (before any agent acts) uses the fixed id `"initial_state"`. No UUID generation. The first trace has `from_id: "initial_state"` and `to_id: <first_real_outcome_id>`.

---

## 8. Data-Oriented Logging Levels

| Level | Purpose | What is stored |
|-------|---------|----------------|
| **0** | Communication | agent_update (with local_knowledge, decision), environment_outcome |
| **1** | Traceability, interpretability | Level 0 + trace and `decision.explanation` populated |
| **2** | Accountability, provenance | Level 1 + provenance and accountability on envelope |

At Level 0: agent_update has local_knowledge and decision (no explanation). At Level 1: traces are stored and decision also includes explanation. At Level 2: envelope has provenance and accountability.

---

## 9. State Equivalence and Deduplication

### 9.1 Overview

Environment outcomes represent **states**. When the environment reaches a state it has visited before, the outcome should be deduplicated: the trace's `to_id` points to the existing outcome rather than creating a duplicate. This allows traces to form a **directed graph** of states and transitions, not just a linear chain.

### 9.2 Equivalence Definition

Two outcomes are **equivalent** when their state content is identical. State content is determined by a **hash function** applied to the outcome payload.

- **Default hash input:** State-category fields only (`observations`, `done`). Transition fields (`actions`, `rewards`) and temporal fields (`round`) are excluded, so revisiting the same physical state at different rounds correctly deduplicates.
- **Scenario-defined hash input:** Users may provide a custom `state_hash_fn` that selects different parts of the payload. For example, a gridworld scenario might hash only agent positions and landmark positions.
- **Hash algorithm:** SHA-256 of the canonical JSON serialisation (keys sorted, deterministic). The adapter stores the hex digest.

### 9.3 Index Ownership

The `state_hash → outcome_id` index is owned and maintained by the **adapter**:

- Adapters that support deduplication implement `lookup_outcome_by_hash(state_hash) -> Optional[str]` and `index_outcome(state_hash, outcome_id) -> None`.
- Adapters that do **not** support deduplication skip the index — every outcome is new. This is valid; deduplication is an optimisation, not a requirement.
- The index lives for the duration of the adapter's lifetime (single run for in-memory; persisted sidecar for file-based if needed).

### 9.4 Write Flow

When `RecordWriter.on_outcome_and_traces()` records an environment outcome:

1. **Compute hash:** Apply `state_hash_fn` (or default) to the outcome payload → `state_hash`.
2. **Lookup:** Call `adapter.lookup_outcome_by_hash(state_hash)`.
3. **If found:** Reuse the existing `outcome_id`. Do **not** write a new outcome record.
4. **If not found:** Write the new outcome record. Call `adapter.index_outcome(state_hash, outcome_record.id)`.
5. **Write traces:** Use the (possibly reused) `outcome_id` as `to_id`. Traces are always new — they carry temporal metadata (round, timestamp) specific to this transition.

### 9.5 Outcome Purity

Outcomes represent pure state — no temporal metadata:

- `round`, `timestamp` live on the **trace**, not on the outcome.
- `rewards` are part of the state transition, not the state itself. Whether to include them in the outcome payload or move them to the trace is scenario-dependent. The default includes them in the outcome payload.

### 9.6 Dedup is On by Default

Deduplication is **enabled by default** using `default_state_hash` (SHA-256 of the full canonical payload). This ensures traces form a proper directed graph rather than a linear chain.

- `Session()` → dedup ON with `default_state_hash`.
- `Session(state_hash_fn=custom_fn)` → dedup ON with a scenario-specific hash (e.g. hash only observations, ignoring round/rewards).
- `Session(state_hash_fn=None)` → dedup OFF (escape hatch for edge cases).
- Adapters without `lookup_outcome_by_hash` / `index_outcome` silently skip dedup (no error).

**Design alternatives considered:**
- *Opt-in dedup* (user must explicitly pass `state_hash_fn`). Rejected because the trace graph is a core architectural concept; disabling dedup by default would produce degenerate linear chains that undermine the graph model.
- *Full-payload hash as default* (hash everything including round, actions, rewards). Rejected because identical physical states at different rounds would never deduplicate, producing redundant outcome nodes. The default should hash only state fields to build a meaningful graph.

---

## 10. Shared Data Role

The shared data model serves **two complementary roles**:

| Role | Producer | Consumer | Record kinds |
|------|----------|----------|-------------|
| **World log** | Environment | Analysts, dashboards, post-hoc tooling | `environment_outcome`, `trace` |
| **Agent exchange medium** | Agents | Other agents (via `visible_records`) | `agent_update` |

Both roles use the same record envelope, adapters, and logging levels. The `kind` field distinguishes what the record represents; the `actor` field identifies who produced it. The environment is a data producer (not a decision-maker) that writes outcome records using the same envelope as agents.

**Design alternative considered:** Separate stores for world log vs agent exchange. Rejected because a single shared model is simpler, enables cross-cutting queries (e.g. "which agent_update enabled this outcome?"), and aligns with the DOA principle that all state changes are observable through one medium.

---

## References

- CIP-0002: Shared Data Model as Agent Interface
- CIP-0001: Library First Architecture (logging levels)
- [Adapter Contract](adapter-contract.md) — implementation guidance for `SharedDataAdapter`, including dedup
- Backlog: 2026-02-16_data-model-spec
