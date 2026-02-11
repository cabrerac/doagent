---
author: "Christian Cabrera"
created: "2026-02-02"
id: "0002"
last_updated: "2026-02-05"
status: "In Progress"
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
- [ ] Implemented - Work complete, awaiting verification
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
- [ ] Implement more complex adapters

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

## References
- None yet
