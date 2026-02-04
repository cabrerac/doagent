---
author: "Christian Cabrera"
created: "2026-02-04"
id: "0009"
last_updated: "2026-02-04"
status: "Proposed"
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
- [ ] Accepted - Approved, ready to start work
- [ ] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

## Summary
Add an optional accountability field to the record envelope so decisions are attributable to owner, policy, and responsibility scope without a separate record type.

## Motivation
Accountability (ownership, responsibility, governance context) ensures decisions can be reviewed, challenged, and governed. Keeping it on the same record as provenance keeps reads simple and audits self-contained.

## Detailed Description
Iteration 1 focuses on the accountability structure and record envelope extension.

Options considered:
- **Option A1**: Extend Contribution with accountability fields (mixes lineage with responsibility).
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
- [ ] Define accountability structure
- [ ] Extend record envelope and new_record
- [ ] Add helper, example, tests, and README

## References
- None yet
