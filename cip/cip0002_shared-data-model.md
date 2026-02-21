---
author: "Christian Cabrera"
created: "2026-02-02"
id: "0002"
last_updated: "2026-02-21"
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

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [x] In Progress - Actively being implemented
- [x] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

## Summary
Define a shared data model that acts as the primary interface for agent communication, with a clear record envelope, listen semantics, and provenance support.

## Motivation
To make data orientation the default, agents should communicate through a shared data model rather than direct message passing. This enables interpretability, traceability, and system-level inspection.

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
- [x] Define record envelope and provenance schema
- [x] Document listen semantics and filters
- [x] Implement file-based adapter
- [x] Update tests and example usage
- [x] State deduplication contract and implementation
- [x] Formalised environment_outcome payload structure
- [x] Adapter contract documentation (core + dedup extension)
- [x] Trace graph and dedup test suite (12 tests)
- [x] Collection-per-kind storage refactor (all adapters)
- [x] Dedup on-by-default (`default_state_hash`)
- [x] MongoDB adapter (`MongoSharedData`)
- [ ] Database adapter (Postgres, SQL  — deferred, no immediate use case)
- [ ] Stream adapter (Kafka, Redis — deferred, no immediate use case)

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

## References
- [Data Model Specification](../docs/data-model-spec.md) — Record kinds, roles, relationships, provenance/accountability, trace schema, logging levels.
- [Adapter Contract](../docs/adapter-contract.md) — SharedDataAdapter implementation guide, collection-per-kind model, dedup extension.
