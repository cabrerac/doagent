# DOAgent Shared Data Model Specification

This document specifies the shared data model used for agent communication, coordination, traceability, and accountability. It serves as the reference for implementation (CIP-0002) and for data-oriented logging levels (REQ-0001 / CIP-0001).

---

## 1. Design Choices

| Choice | Decision | Rationale |
|--------|----------|-----------|
| **Structure** | Flat event log | Records are written one-by-one as events occur; grouping is a read/query concern. Supports streaming and adapter flexibility. |
| **Provenance & accountability** | Record envelope only | Single source of truth per record; no duplication inside payloads. |
| **Agent activity** | One agent_update per agent per step | Default design; provenance typically has one contributor per record. |
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

**Role:** The environment's response after an env step. Records the resulting state.

**Payload:** Domain-specific. Common optional slots:
- `reward` / `rewards`: Scalar or per-agent
- `env_status`: Observations, done flag, status
- `actions`: Actions taken (if env records them)
- `round`: Step index

**Structure:** Envelope fixed; payload is open key-value. Each scenario defines its own structure.

---

### 4.2 reward, env_status

**Conceptual components** of environment_outcome, not separate record kinds. The payload may expose `reward` and `env_status` as top-level keys.

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
| **Provenance** | Authorship. *Who produced this record?* Which agent's code ran and wrote this output. |
| **Accountability** | Responsibility. *Who answers for this record?* Can differ from authorship (delegation, team ownership, policy). |

**Provenance schema:** `contributions`: list of `{agent, sources, tools, notes}`.

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

When recording an environment outcome:
1. Compute hash of the state (scenario-defined what is included)
2. Check if equivalent state exists via `state_hash → outcome_id` index
3. If yes: reuse existing outcome id for `to_id`; write new trace
4. If no: create new outcome; index it; write trace

**Metadata:** Temporal info (round, timestamp) lives on the trace, not on the outcome. Outcomes stay "pure state."

**Adapter responsibility:** Adapters that support deduplication maintain the index. JSON: in-memory or sidecar. DB: native indexes. Streams: medium-specific.

---

## References

- CIP-0002: Shared Data Model as Agent Interface
- CIP-0001: Library First Architecture (logging levels)
- Backlog: 2026-02-16_data-model-spec
