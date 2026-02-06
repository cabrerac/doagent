---
author: "Christian Cabrera"
created: "2026-02-04"
id: "0007"
last_updated: "2026-02-05"
status: "In Progress"
compressed: false
related_requirements:
- "0007"
related_cips: []
tags:
- cip
- traceability
- architecture
title: "Trace Records and Lineage Links"
---

# CIP-0007: Trace Records and Lineage Links

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
Introduce trace records that link inputs to outputs, enabling decision and message chains to be reconstructed from shared data.

## Motivation
Traceability allows users to navigate from outcomes back to the records, agents, and tools that influenced them without accessing live agent runtimes.

## Detailed Description
Iteration 1 focuses on trace data structures and linkage.

Options considered:
- **Option A**: embed trace links in record payloads.
- **Option B**: extend provenance to carry trace links.
- **Option C**: store trace links as separate records.

We select a hybrid of **Option B + C**:
- Trace edges are stored as separate records (append-only graph).
- Records may reference trace identifiers in provenance for efficient lookup.

Key points:
- Trace records are `SimpleRecord` entries with `kind="trace"`.
- Trace payloads include `from_id`, `to_id`, and a small `relation` label.
- Optional fields include `actor`, `timestamp`, and `notes` for richer context.
- Provenance can include optional trace references for fast association.

Scalability considerations:
- Trace writes must be lightweight and optional to avoid slowing agent actions.
- Payloads should remain compact and append-only to reduce write overhead.
- Trace lookups should prefer id-based retrieval to avoid full scans.
- Batching and retention policies should be considered in later iterations.

## Iteration Deliverable (PoC)
- Trace payload structure (including optional fields) and conventions.
- Helper for creating trace records.
- Example and tests for linking records via trace edges.

## Implementation Plan
1. **Define trace payload structure**
   - Minimal fields for `from_id`, `to_id`, and `relation`.
2. **Add creation helper**
   - Helper to create trace records with `kind="trace"`.
3. **Update examples and tests**
   - Minimal example and unit tests for trace linkage.
4. **Document usage**
   - Add README entry for trace records and lookup guidance.

## Backward Compatibility
No backward compatibility impact; this introduces a new record type.

## Testing Strategy
- Unit test for trace record creation and linkage.
- Example demonstrating decision → trace → upstream inputs.

## Related Requirements
This CIP addresses the following requirements:
- REQ-0007: Traceability of Decision Chains

## Implementation Status
- [x] Define trace payload structure
- [x] Add creation helper
- [x] Update examples and tests
- [x] Document usage

## Progress Updates

### 2026-02-04
Iteration 1 complete. Trace payload, helper, tests, and examples added. Tests passed. Iteration 2 planned. Next iteration should focus on trace retrieval patterns (e.g., graph traversal helpers) and optional provenance links at scale.

Trace records now link decisions and messages through append-only edges. The payload stays compact while allowing optional context fields, which supports traceability without heavy write overhead.

Gaps and follow-on needs:
- Provide retrieval helpers for walking trace chains efficiently.
- Clarify provenance references to trace ids for fast association.
- Make trace creation transparent to library users with configurable defaults (global vs local tracing).
- Align trace/explanation automation so users can tune granularity without manual record handling.

### 2026-02-06
Iteration 2 questions to support across scenarios (environment-agnostic):
- Which actions most directly influenced an outcome?
- Where do causal chains fork or converge across agents?
- Are observed changes immediate or delayed effects?
- Can outcomes be traced to a minimal set of upstream decisions?

These questions should be answerable without relying on environment-specific mechanics.

## References
- None yet
