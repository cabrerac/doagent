---
author: "Christian Cabrera"
created: "2026-02-04"
id: "0008"
last_updated: "2026-03-04"
status: "In Progress"
compressed: false
related_requirements:
- "0008"
related_cips: []
tags:
- cip
- provenance
- architecture
title: "Provenance Semantics and Helper"
---

# CIP-0008: Provenance Semantics and Helper

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
Formalise provenance semantics (creation-time attribution, one contribution per agent) and add a helper to build provenance for records. Trace sync from provenance is deferred to a later iteration.

## Motivation
Provenance answers who created a record and what they used (sources, tools). Making semantics explicit and providing a helper reduces errors and keeps records auditable.

## Detailed Description
Iteration 1 focuses on formalising current provenance and easing its use.

Options considered:
- **Option A**: Formalise semantics + add helper; document relation to traces; defer auto-write of traces.
- **Option B**: Same as A and implement sync in this iteration (auto-write one trace per contribution source).
- **Option C**: Add optional trace_ids to provenance to reference trace records.

We select **Option A**. Provenance remains the source of truth for creation-time attribution; synchronisation of trace records from contribution.sources will be implemented in a later iteration (with transparent trace/explanation handling).

Key points:
- Provenance is creation-time attribution: who created this record and what they used (derived_from = input record ids, used_tools, notes).
- One flat attribution per record — matches the design choice of one agent_update per agent per step.
- Relation to traces: one trace edge per derived_from source (from_id=source, to_id=record.id) will be derived from provenance in a later iteration; provenance is the source of truth.

## Iteration Deliverable (PoC)
- Documented provenance semantics.
- Helper to build flat Provenance from (agent, sources, tools, notes).
- Example and tests for records created with provenance via the helper.
- README note on provenance and planned trace sync.

## Implementation Plan
1. **Document provenance semantics**
   - In CIP and docstrings: creation-time, flat attribution, relation to traces (deferred).
2. **Add provenance helper**
   - Helper (`new_provenance`) to build a flat Provenance dict for use with new_record.
3. **Update examples and tests**
   - Example and unit tests for record creation with provenance via helper.
4. **Document usage**
   - README entry for provenance and planned trace sync.

## Backward Compatibility
No breaking changes; existing records and new_record(provenance=...) remain valid. Helper is additive.

## Testing Strategy
- Unit test for helper output and record round-trip with provenance.
- Example showing record created with provenance via helper.

## Related Requirements
This CIP addresses the following requirements:
- REQ-0008: System Wide Provenance

## Implementation Status
- [x] Document provenance semantics
- [x] Add provenance helper
- [x] Update examples and tests
- [x] Document usage

## Iteration 2 Plan: doagent.analysis.provenance

Promote analysis capabilities into a first-class library module. Iteration 2 adds `doagent.analysis` with property-based submodules; provenance is one of four.

**Deliverable**: `doagent.analysis.provenance` submodule
- `walk_chain(record_id, records_source, max_depth)` — walk derived_from chain backwards, return structured chain
- `render_chain_tree(record_id, records_source, output_path)` — produce tree diagram (PNG/PDF)
- Records source: Path, SharedDataAdapter, or dict of record lists
- Environment-agnostic: works with any DOAgent run output

**Design**: Group analyses by the property they enable. User imports `from doagent.analysis import provenance`. Provenance chain walking answers "who created what from what?" without agent internals. Future: auto-trace sync from derived_from (separate iteration).

**Related backlog**: 2026-03-04_analysis-module-library

## Progress Updates

### 2026-02-04
Iteration 1 complete. Provenance semantics documented, helper added, tests and example added. Tests passed. Iteration 2 planned. Trace sync from provenance (one trace per source) deferred to a later iteration.

Provenance is now explicit as creation-time attribution with one flat attribution per record; the helper makes it easy to attach provenance when creating records. Outputs can be traced to inputs and tools via `derived_from` and `used_tools`. Trace edges derived from provenance will be added in a later iteration so graph traversal stays in sync with record-level attribution.

Gaps and follow-on needs:
- Implement automatic trace record creation from `derived_from` sources when a record is written (provenance as source of truth).
- Consider making provenance attachment transparent at the write path (e.g. adapter or agent layer) with optional user controls, consistent with CIP-0007 reflection.

### 2026-02-06
Iteration 2 questions to support across scenarios (environment-agnostic):
- What exact inputs and context produced this decision?
- Which external factors (randomness, initial conditions, configs) were in play?
- Can we reproduce outcomes from recorded provenance alone?
- What hidden state should be surfaced to make provenance complete?

These questions should be answerable without assuming a specific environment or toolchain.

### 2026-03-04
Iteration 2 plan added: `doagent.analysis.provenance` submodule. See Iteration 2 Plan section.

### 2026-01-28
Analysis demo delivered: provenance_walker.py walks derived_from chains backwards from any record. Demonstrates provenance as source of truth for "who created what from what." Iteration 2 auto-trace sync from derived_from would reduce manual trace creation.

## References
- None yet
