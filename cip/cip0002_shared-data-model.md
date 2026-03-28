---

author: "Christian Cabrera"
created: "2026-02-02"
id: "0002"
last_updated: "2026-03-27"
status: "Implemented"
compressed: false
related_requirements:

- "0002"
- "0008"
related_cips: []
tags:
- cip
- shared-data
- architecture
title: "Shared Data Model as Agent Interface"

---

# CIP-0002: Shared Data Model as Agent Interface

> **Note**: CIPs describe HOW to achieve requirements (WHAT).
> Use `related_requirements` to link to the requirements this CIP implements.

## Status

- Proposed - Initial idea documented
- Accepted - Approved, ready to start work
- In Progress - Actively being implemented
- Implemented - Work complete, awaiting verification
- Closed - Verified and complete
- Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- Deferred - Postponed (use blocked_by field to indicate blocker)

## Summary

Define a shared data model that acts as the primary interface for agent communication, with a clear record envelope, listen semantics, and provenance support.

## Motivation

To make data orientation the default, agents should communicate through a shared data model rather than direct message passing. This enables interpretability, traceability, and system-level inspection. In a future iteration, the shared data model should support **policy factorization** (the split between *reason* and *action*): the ability to record and query reasoning traces separately from external actions, so that "what the agent thought" is observable alongside "what it did" (see §2.2 of the agentic reasoning reading guide in `papers/agentic-reasoning-llm-reading-guide.md`).

## Detailed Description

This CIP formalises the shared data model and its record semantics. It builds on the PoC by:

- Defining a canonical record envelope and versioning approach.
- Clarifying `listen` semantics for kind-based consumption.
- Providing provenance hooks as first-class fields in the record structure.
- Establishing rules for record immutability and append-only behaviour.

### Record Envelope

Define a simple record envelope with:

- `id`, `timestamp`, `actor`, `kind`, `payload`, `provenance`

### Listen Semantics

For the next iteration:

- `listen(kind)` yields records in insertion order.
- Allow optional filtering by actor and time window (if available).

### Provenance

Require provenance metadata to include:

- `sources` (input record ids)
- `tools` (optional tool identifiers)

### Future iteration: Policy factorization (reason vs. action)

The shared data model does not yet support the **reason–action split** from the agentic reasoning framework (policy factorization: π(a_t, z_t | h_t) = π^reason(z_t | h_t) · π^act(a_t | h_t, z_t)). Today we record explanations (human-readable rationale) attached to decisions, but we do not model or expose:

- A first-class **reasoning trace** (z_t) distinct from the **external action** (a_t)
- Observability of that split (e.g. querying reasoning separately from actions, or tracing "this action was conditioned on this reasoning step")

Supporting this in a future iteration would strengthen interpretability (REQ-0006), traceability (REQ-0007), and provenance/accountability (REQ-0008, REQ-0009). Possible directions (to be discussed when implementing): first-class reasoning records, structured reason+action fields in the payload, or API-level reason/act steps with explicit linkage in the substrate. No implementation commitment in this CIP; this is a documented requirement for a later iteration.

### Future iteration: Shared data as agentic shared memory (M)

In the agentic reasoning framework, **M** (internal memory/context) summarizes history h_t so that the next step can be conditioned on it. The shared data substrate already holds the content that could form M (all records, trace, provenance). Consumers of the shared data model are **both** policies (at decision time, as shared memory) and end users (for analysis).

**Agreed design for a future iteration:**

- **Memory** — What counts as memory is tied to what each agent defines. The library should provide something explicitly called **memory** (like `inspect`), so that "shared data as M" is a named, first-class concept. Initially the library provides the **raw data** (topology-respecting view); we could add **adapters** later (e.g. summarization, custom shape) so that memory can be agent- or scenario-defined without changing the entry point. So: `**session.memory(agent_id, kind=None, ...)`** — semantics "records that form this agent's shared memory (context) for the next decision"; respects topology (same as `visible_records`); default implementation may mirror `visible_records` with a documented ordering. No oracle on memory: how knowledge is shared depends on observability (topology).
- **Oracle mode** — Makes sense for **analysis only**, not as shared memory. A way for end users or tooling to obtain a privileged view (full history regardless of topology) for debugging, simulation, or inspection. Separate from the memory API: e.g. `session.inspect(..., as_oracle=True)` or `session.oracle_view(kind)` for analysis-time use only.

Implementation: add `session.memory(agent_id, ...)` as the memory entry point; add oracle as a separate analysis-time surface. No implementation commitment in this CIP; this is a documented requirement for a later iteration.

(Current surfaces: `inspect(kind)` for post-run analysis; `visible_records(agent_id, kind)` for topology-filtered context at decision time.)

### Future iteration: Reasoning-centric memory

The agentic reasoning paper emphasises **reasoning-centric memory**: memory that supports how agents reason over time. That implies several capabilities we should consider or provide:


| Capability                 | Meaning                                                                                                                  |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Task semantics**         | Memory organised or scoped by task/goal (e.g. "memory for this task", "what we did for goal X").                         |
| **Temporal dependencies**  | Order and causality: what happened when, what led to what.                                                               |
| **Agentic control**        | **When** and **what** to write: the agent (policy) decides what to commit to memory, not a fixed "dump every step" rule. |
| **Search and memory loop** | Query memory → use in reasoning → optionally write → query again (read–reason–write–read).                               |
| **Self-evolving state (S_k)** | Evolvable state across episodes (e.g. reflections, tool registries); meta-updates observable. Addressed by the same **search** features: e.g. `session.search(from, to)` or time/episode-scoped queries surface S_k when the substrate persists across runs. |


**Stance: enabler first, optional library solutions.** DOAgent should **enable** these capabilities (primitives, data model, extension points) so users can build reasoning-centric memory on top; we can **optionally offer** thin helpers where the pattern is clear (e.g. a standard way to write to memory from a policy, or a search hook that adapters implement). This aligns with library-first and model-agnostic tenets.

**Naming helpers for agentic reasoning.** As with `inspect` for observability, we should provide helpers that sound closer to the concepts we are enabling: e.g. `memory` (shared memory view), `search_memory` (query over memory), `write_memory` (agent-controlled write), or task-scoped views. The API then reads naturally for anyone thinking in agentic-reasoning terms, even when the implementation delegates to the same substrate (listen, visible_records, new record kinds).

**Current state vs future:**

- **Temporal:** We already have timestamps, insertion order, and the trace graph (from_id/to_id). Temporal structure is largely in place; we can add small helpers (e.g. "memory since t", "in causal order") as part of the memory work.
- **Task semantics:** Not yet. Enabler = optional task_id or tags on the envelope/payload so records can be scoped by task; users or adapters index/filter. Optional helper = e.g. `session.memory(agent_id, task_id=...)` if we add the dimension.
- **Agentic control (when/what to write):** Today recording is implicit (every step → agent_update, outcome, trace). Enabler = a record kind (e.g. `memory` or `agent_memory`) that policies can ask the session to write, plus traceability. Optional helper = e.g. `session.write_memory(agent_id, content, ...)`.
- **Search and memory loop:** Today we have listen(kind) and topology filtering only. Enabler = richer query/filter surface or an adapter extension point for search. Optional helper = e.g. `session.search_memory(agent_id, query=...)` or `session.search(from, to)` (time/episode range) delegating to an optional backend. **Self-evolving S_k** (evolvable memories across episodes) is part of this: search over a persistent substrate that spans runs naturally surfaces S_k (reflections, tool registries, etc.) and makes meta-updates observable.

**Meta-update as a record kind.** The paper’s meta-update U(S_k, F_k) (evolvable state updated from feedback at the end of an episode) can be modeled as a **new record kind**, in the same spirit as policy factorization: we make the transition first-class and traceable. A record (e.g. `meta_update` or `evolvable_state_update`) would capture what changed in S from episode k to k+1, when it happened, and the feedback F_k that drove it (via provenance/sources), so that how state evolved is observable and attributable. To be discussed in a future iteration alongside policy factorization and other new record kinds.

What to implement (task_id, write_memory, search / search_memory, temporal helpers, S_k via search, and meta-update record kind) will be discussed and decided in a future iteration. No implementation commitment in this CIP; this documents the capabilities and the enabler-plus-helpers direction.

## Iteration Deliverable (PoC)

- Expand the record envelope to include provenance fields with a documented structure.
- Extend `listen` semantics with optional filters.
- Add a second shared-data adapter (file-based or simple log) to validate portability.

## Implementation Plan

1. **Formalise record envelope**
  - Document required fields and provenance schema.
2. **Define listen semantics**
  - Clarify filters and ordering behaviour.
3. **Implement second adapter**
  - Provide a file-based append-only adapter.
4. **Update examples and tests**
  - Add tests for provenance fields and listen filters.

## Backward Compatibility

Record shape changes should be backwards compatible by keeping optional fields.

## Testing Strategy

- Unit tests for record validation and provenance fields.
- Integration tests for `listen` filters and ordering.
- Adapter parity tests between in-memory and file-based storage.

## Related Requirements

This CIP addresses the following requirements:

- REQ-0002: Shared Data Model as Agent Interface
- REQ-0008: System Wide Provenance

## Implementation Status

- Define record envelope and provenance schema
- Document listen semantics and filters
- Implement file-based adapter
- Update tests and example usage
- State deduplication contract and implementation
- Formalised environment_outcome payload structure
- Adapter contract documentation (core + dedup extension)
- Trace graph and dedup test suite (12 tests)
- Collection-per-kind storage refactor (all adapters)
- Dedup on-by-default (`default_state_hash`)
- MongoDB adapter (`MongoSharedData`)
- Database adapter (Postgres, SQL  — deferred, no immediate use case)
- Stream adapter (Kafka, Redis — deferred, no immediate use case)
- Policy factorization (reason vs. action) — future iteration; see "Future iteration: Policy factorization" in Detailed Description
- Shared memory API (`session.memory(agent_id, ...)`) — future iteration; see "Future iteration: Shared data as agentic shared memory (M)" in Detailed Description
- Oracle mode for analysis (e.g. `oracle_view` or `inspect(..., as_oracle=True)`) — future iteration; analysis-only, separate from memory
- Reasoning-centric memory (task semantics, temporal helpers, agentic control/write_memory, search and memory loop) — future iteration; see "Future iteration: Reasoning-centric memory" in Detailed Description; enabler first, optional helpers named for agentic reasoning (like inspect for observability)

## Progress Updates

### 2026-02-02

Iteration 1 complete. Record envelope, listen semantics, file adapter, and tests updated. Tests passed. Iteration 2 planned. Next iteration should implement more complex adapters. This might require an architectural shift (i.e., a new CIP).

### 2026-02-06

Iteration 2 discussion item: review record envelope redundancy observed in validation output. Candidates include duplicate `accountability`/`provenance` inside decision payloads (already present at the record level) and empty `accountability`/`provenance` fields on explanation/trace/outcome records. Consider making these optional or removing duplicates to reduce noise.

### 2026-02-06

Iteration 2 discussion items:

- Provenance has a defined type but accountability does not; assess whether to formalize an accountability type (reduce ambiguity) or keep it loose (reduce redundancy).
- Decide on acceptable redundancy in the record envelope (read-vs-write tradeoff) and document a standard.
- Clarify whether shared data is primarily a world log, a medium for agent-to-agent exchange, or both. In the current validation flow agents and the environment writes outcomes but agents do not read from shared data; decide if this is intentional or should change in later iterations.
- Formalising the model (record schema, kind semantics, indexing/query patterns) gives a spec that adapters must implement. That keeps InMemorySharedData and FileSharedData as “flat” implementations, while Mongo/SQL adapters map to richer structures, without changing the public API. A single, explicit data model for all adapters makes sense; the difference is how each adapter maps that model to its storage (flat vs collections vs tables).
- The environment writes in the shared data model as it was an agent. Does it make sense?

### 2026-02-21 — Discussion items resolved

All four iteration 2 discussion items are now resolved:

1. **Envelope redundancy**: Already handled. The data model spec (§1) states provenance/accountability live on the envelope only — no duplication inside payloads. The Session API strips these from policy responses before building the decision payload. Empty `{}` at Levels 0-1 is acceptable (§2: "may be omitted or minimal"); a predictable schema is preferable to optional keys.
2. **Accountability type**: Resolved. `Accountability` is a formal `TypedDict` (§6: `owner`, `policy_id`, `responsibility_scope`). `SimpleRecord.accountability` now typed as `Accountability` instead of `Dict[str, Any]`, matching how `provenance` uses the `Provenance` type.
3. **Shared data role**: Resolved. Added §10 to the data model spec: shared data is **both** a world log (environment writes outcomes) and an agent exchange medium (agents write `agent_update`, read via `visible_records`). Single store enables cross-cutting queries.
4. **Environment as actor**: Resolved. The data model spec (§2) defines `actor` as "Entity that produced the record (agent id, env id)". The env is a data producer, not a decision-maker. The `kind` field (`outcome` vs `agent_update`) distinguishes roles. This is consistent with the DOA principle that all state changes are observable. For next iteration, we should discuss about scenarios where environments offer partial or not outcomes.

Additionally: **Stream adapter deferred.** Kafka/Redis adapter requires external infrastructure with no immediate use case in validation scenarios. Marked as future iteration. The same for **SQL adapter**.

### 2026-02-21

Iteration 2 implementation — state deduplication, outcome formalisation, adapter contract:

- **State dedup contract** (§9 of data-model-spec): equivalence via SHA-256 of canonical JSON; scenario-defined `state_hash_fn`; adapter-owned index; opt-in via `Session(state_hash_fn=...)`.
- **Outcome payload** (§4.1): formalised recommended keys (observations, done, rewards, actions, round) with category semantics (state/transition/temporal) for dedup alignment. Added `done` to `RecordWriter.on_outcome_and_traces()`.
- **Adapter contract** (`docs/adapter-contract.md`): core interface guarantees + optional `lookup_outcome_by_hash`/`index_outcome` dedup extension. Implementation guidance for in-memory, file, DB, and stream backends.
- **Adapter implementations**: `InMemorySharedData` and `FileSharedData` both have dedup index (in-memory dict).
- **Tests**: 12 new tests in `tests/test_trace_dedup.py` covering trace graph structure, state dedup, multi-trace reuse, file adapter dedup, and opt-out behaviour.
- All 61 tests pass (49 existing + 12 new).

### 2026-02-21

Collection-per-kind storage refactor, dedup-on-by-default, MongoDB adapter:

- **Dedup on-by-default**: `Session` now uses `default_state_hash` by default. Traces form a proper graph out-of-the-box. Explicit `state_hash_fn=None` opts out (escape hatch).
- **Collection-per-kind storage**: All adapters now organise records by kind. `InMemorySharedData` uses `Dict[kind, Dict[id, SimpleRecord]]`. `FileSharedData` uses one `<kind>.jsonl` file per kind in a directory. `MongoSharedData` uses one MongoDB collection per kind. This makes `listen()` efficient and aligns all adapters to the same conceptual model.
- **MongoSharedData** (`doagent/core/mongo_shared_data.py`): New MongoDB adapter with collection-per-kind layout, native query filters in `listen()`, `_state_index` collection for dedup, and `ensure_indexes()` for recommended indexes. Requires `pymongo` (optional dependency; import guarded).
- **Design alternatives documented** in `docs/adapter-contract.md` §6: flat-store vs collection-per-kind, opt-in vs default dedup, adapter vs writer-owned index, hash computation location, MongoDB `_id` strategy.
- **Tests**: 11 new MongoDB adapter tests via `mongomock`. Total: 72 passed, 3 skipped.

### 2026-02-21

Provenance flattened from `contributions: List[Contribution]` to flat attribution (`created_by`, `derived_from`, `used_tools`, `notes`). The list-of-contributions structure implied collaborative multi-agent authorship of a single record, which does not match the actual write model (one agent_update per agent per step). Updated: `Provenance` TypedDict, `new_provenance()` helper, data-model-spec §6, CIP-0008, README, all tests and examples.

### 2026-03-13

Documented **policy factorization (reason vs. action)** as a future iteration requirement. The shared data model does not yet support the split between reasoning trace (z_t) and external action (a_t) or the observability that split enables. Added to Motivation, a "Future iteration" subsection in Detailed Description, and an unchecked Implementation Status item. Implementation options (first-class reasoning records, structured payload fields, API-level reason/act steps) to be discussed in a future iteration. See `papers/agentic-reasoning-llm-reading-guide.md` for the source framework.

Documented **shared data as agentic shared memory (M)** for next iterations. Agreed: consumers are both policies (shared memory at decision time) and end users (analysis); memory is what each agent defines, with the library providing raw data initially and optional adapters later; oracle mode is for analysis only (full visibility), not shared memory, since how knowledge is shared depends on observability/topology. The library will provide an explicit **memory** API (e.g. `session.memory(agent_id, ...)`), like `inspect`, even if initially similar to `visible_records` — names the concept and gives a stable entry point for future adapters. Oracle to be a separate analysis-time surface (e.g. `oracle_view` or `inspect(..., as_oracle=True)`). Updated "Future iteration: Shared data as agentic shared memory (M)" and Implementation Status accordingly.

Documented **reasoning-centric memory** as a future iteration theme. Added subsection "Future iteration: Reasoning-centric memory" covering: task semantics, temporal dependencies, agentic control (when/what to write), search and memory loop. Stance: DOAgent as enabler first (primitives, data model, extension points), with optional library solutions (thin helpers). Emphasised naming helpers to align with agentic reasoning — like `inspect` for observability, we should offer APIs that read naturally in those terms (e.g. `memory`, `search_memory`, `write_memory`, task-scoped views). Current state: temporal structure largely in place (trace, timestamps); task semantics, agentic write path, and search to be discussed and decided later. Implementation Status updated with one umbrella item for reasoning-centric memory.

Added **self-evolving state (S_k)** to that scope: S_k is not a separate feature but part of the search features we provide (e.g. `session.search(from, to)` or time/episode-scoped queries). When the substrate persists across runs, search over a range naturally surfaces evolvable memories (reflections, tool registries) and makes meta-updates observable. Table and "Search and memory loop" bullet updated accordingly.

**Meta-update as record kind:** Noted that U(S_k, F_k) can be modeled as a new record kind (e.g. `meta_update` or `evolvable_state_update`), same pattern as policy factorization — make the transition first-class and traceable. To be discussed in a future iteration alongside other record kinds.

### 2026-03-27

**Talk-driven iteration (deliberation paused; work tracked in backlog).** Goal: **library-level** support for **policy factorization** (separate observable **reasoning** Z-like step vs **external action** A) aligned with **`papers/agentic-reasoning-llm.md`**, and an **explicit "I don't know" / abstention** path inspired by **`papers/consistent-reasoning-paradox-llm.md`** (demonstration and inspection -- **not** a claim to implement the full formal **IDK function** from the CRP). Slides + **`notebooks/`** for live demo; existing scenarios (push/gridworld) or a minimal toy env to be chosen at implementation time. Primary demo: **one LLM agent** (reliability); optional short **multi-agent** segment for **topology as reasoning context** (**CIP-0003**). Captured as backlog task **`2026-03-27_talk-policy-factorization-idk-library`**.

### 2026-03-28

**Design decisions for policy factorization, IDK, and record format (Stage 2 complete).**

Resolved the following design questions through deliberative discussion:

1. **Record format — `choice` replaces inner `decision`:** The inner commit object moves from `response.decision` to **`response.choice`** containing `status` (`"act"` | `"abstain"` | `"error"`) and `action` (env primitive or `null`). This avoids the `decision.decision` naming collision. The outer `payload.decision` (request/response bundle) is unchanged. Optional `choice.error` for failure details.

2. **Factorization mechanism — Option B (structured field):** Reasoning trace (Z) is recorded as an optional **`response.reasoning`** field inside the existing `agent_update` record, not as a separate record kind. Rationale: inspecting reasoning only makes sense alongside the decision it produced; keeps one `agent_update` per agent per step.

3. **Policy return shape — explicit, no compat shim:** Policies return `{"choice": {status, action}, "reasoning": {...}, "explanation": "..."}`. Old policies and examples will be updated to the new contract rather than maintaining backward compatibility.

4. **Session API — single `decide()` call:** `SessionAgent.decide()` stays as one call. Returns `{"action": response["choice"]["action"], "response": response}`. Callers check `response["choice"]["status"]` to distinguish act/abstain/error. No two-phase `reason()` + `act()` API for this iteration.

5. **Env handling of abstain — library-agnostic:** The library passes `None` as the action when `status != "act"`. The environment itself should understand `None` (or a sentinel) as a valid "no-op / IDK" action. Scenario loops handle it explicitly.

6. **Demo strategy — extend existing notebooks:** No new notebook. Extend `01_minimal_demo` (new choice shape + abstain cell), `02_push_demo` or `03_gridworld_demo` (LLM policy section with factorization + IDK). LLM policy is model-agnostic (pluggable via env var / config).

7. **Record kind name:** `agent_update` stays (not renamed to `decision`) because `record_update()` writes non-decision agent messages (e.g. hub summaries) using the same kind.

**Implementation order (6 sub-tasks, backlog `2026-03-28_*`):**

1. Policy return shape + `decide()` (foundational)
2. Optional `reasoning` field in payload (depends on 1)
3. Update heuristic policies/examples (depends on 1; parallel with 2, 4)
4. Update `data-model-spec.md` (depends on 1 + 2; parallel with 3)
5. Pluggable LLM policy (depends on 1 + 2; parallel with 3, 4)
6. Update notebooks (depends on 3 + 5)

Critical path: 1 → 2 → 5 → 6.

## References

- [Data Model Specification](../docs/data-model-spec.md) — Record kinds, roles, relationships, provenance/accountability, trace schema, logging levels.
- [Adapter Contract](../docs/adapter-contract.md) — SharedDataAdapter implementation guide, collection-per-kind model, dedup extension.

