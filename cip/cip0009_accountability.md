---
author: "Christian Cabrera"
created: "2026-02-04"
id: "0009"
last_updated: "2026-07-28"
status: "Implemented"
compressed: false
related_requirements:
- "0009"
related_cips: []
tags:
- cip
- accountability
- architecture
title: "Accountability on Record Envelope"
---

# CIP-0009: Accountability on Record Envelope

> **Note**: CIPs describe HOW to achieve requirements (WHAT).
> Use `related_requirements` to link to the requirements this CIP implements.

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [ ] In Progress - Actively being implemented
- [x] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

**Implemented** means **iterations 1 and 2** are delivered (accountability envelope field, `new_accountability`
helper, `doagent.analysis.accountability`) and **REQ-0009**'s acceptance criteria are all met. Threading
accountability through the agent write path and conventions for `policy_id` / `responsibility_scope` remain future
iterations — they are listed under Progress Updates and do not block this status.

## Summary
Add an optional accountability field to the record envelope so decisions are attributable to owner, policy, and responsibility scope without a separate record type.

## Motivation
Accountability (ownership, responsibility, governance context) ensures decisions can be reviewed, challenged, and governed. Keeping it on the same record as provenance keeps reads simple and audits self-contained.

## Detailed Description
Iteration 1 focuses on the accountability structure and record envelope extension.

Options considered:
- **Option A1**: Extend Provenance with accountability fields (mixes lineage with responsibility).
- **Option A2**: Add optional `accountability` field on the record envelope (owner, policy_id, responsibility_scope).
- **Option B**: Separate accountability record (e.g. kind="accountability") referencing the record.

We select **Option A2**. Provenance remains lineage (who, sources, tools); accountability is a separate optional envelope field for ownership and governance context. Default is empty so existing records and call paths remain valid.

Key points:
- New type: Accountability (e.g. TypedDict) with optional owner, policy_id, responsibility_scope.
- SimpleRecord gains optional `accountability` field (default empty dict or equivalent).
- new_record accepts optional accountability and passes it through.
- Backward compatible: optional field with default; existing code unchanged.

## Iteration Deliverable (PoC)
- Accountability type and record envelope extension.
- new_record updated to accept optional accountability.
- Optional helper to build accountability for use with new_record.
- Example and tests; README note.

## Implementation Plan
1. **Define accountability structure**
   - TypedDict or similar with optional owner, policy_id, responsibility_scope.
2. **Extend record envelope**
   - Add optional accountability to SimpleRecord; update new_record.
3. **Optional helper and docs**
   - Helper to build accountability dict; example and unit tests; README.

## Backward Compatibility
Optional field with default; existing records and new_record(provenance=...) remain valid. Adapters that persist records must handle the new field (e.g. asdict or serialisation); in-memory and file adapters should be updated to include it.

## Testing Strategy
- Unit test for record creation with accountability and round-trip.
- Example showing record with accountability.

## Related Requirements
This CIP addresses the following requirements:
- REQ-0009: System Wide Accountability

## Implementation Status
- [x] Define accountability structure
- [x] Extend record envelope and new_record
- [x] Add helper, example, tests, and README

## Iteration 2 Plan: doagent.analysis.accountability

Promote analysis capabilities into a first-class library module. Iteration 2 adds `doagent.analysis` with property-based submodules; accountability is one of four.

**Deliverable**: `doagent.analysis.accountability` submodule
- `causal_attribution(records_source)` — per-agent contribution from trace edges, return structured dict
- `render_attribution_charts(attribution, output_path)` — line chart (cumulative discovery), bar chart (total discovery), effectiveness chart (productive vs redundant)
- Attribution logic uses agent-specific observations (not first-agent-wins)
- Records source: Path, SharedDataAdapter, or dict of record lists
- Environment-agnostic: works with any DOAgent run output

**Design**: Group analyses by the property they enable. User imports `from doagent.analysis import accountability`. Causal attribution answers "who contributed what?" with evidence from trace data. Extensible for policy-level attribution, adversarial settings.

**Related backlog**: 2026-03-04_analysis-module-library

## Progress Updates

### 2026-07-28
CIP marked **Implemented**. Verified against REQ-0009: all three acceptance criteria are checked and the requirement
already reads `Implemented`. All Implementation Status items are complete, and the covering tests pass
(`test_accountability`, `test_analysis_accountability`) in a run of 104 passed / 3 skipped. Mongo-backed tests were
not exercised in that run (no `pymongo` in the interpreter used), so file storage is the verified substrate.

### 2026-02-05
Iteration 1 complete. Accountability TypedDict, optional envelope field, `new_accountability` helper, file-adapter backward compatibility, tests, example, and README added. Tests passed. Iteration 2 planned.

Accountability is now an optional envelope field (owner, policy_id, responsibility_scope) separate from provenance; the helper and default empty dict keep existing records and call paths valid. Audits can read ownership and governance context from the same record.

Gaps and follow-on needs (candidates for iteration 2):
- Consider threading accountability through agent write path (e.g. optional accountability on `AgentAdapter.write` or decision agents) so agents can attach ownership without calling `new_record` directly.
- Optional validation or conventions for policy_id / responsibility_scope (e.g. namespaced identifiers) if governance tooling is added later.

### 2026-03-04
Iteration 2 plan added: `doagent.analysis.accountability` submodule for causal attribution. See Iteration 2 Plan section.

### 2026-02-06
Iteration 2 questions to support across scenarios (environment-agnostic):
- Who is responsible for a poor outcome: policy owner, configuration owner, or environment setup?
- How do we attribute accountability in competitive or adversarial settings?
- Should accountability capture policy versions and run configurations?
- What accountability scope is appropriate for multi-agent interactions?

These questions should be answerable without relying on a specific environment.

## References
- None yet
