---
author: "Christian Cabrera"
created: "2026-02-04"
id: "0006"
last_updated: "2026-02-05"
status: "In Progress"
compressed: false
related_requirements:
- "0006"
related_cips: []
tags:
- cip
- interpretability
- architecture
title: "Interpretability Records"
---

# CIP-0006: Interpretability Records

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
Add interpretability records that attach human-readable explanations to decision records via the shared data model.

## Motivation
Interpretability should be available without accessing agent runtimes. Storing explanations as shared data keeps decisions auditable and retrievable.

## Detailed Description
Iteration 1 focuses on data structures and linkage.

Options considered:
- **Option A**: extend `SimpleRecord` with interpretability fields.
- **Option B**: store explanations as separate records linked to decisions.

We selected **Option B**. Interpretability artefacts are stored as separate records linked to decision records via a shared identifier. The approach keeps the core record envelope stable and allows multiple explanations per decision.

Key points:
- Decision records remain standard `SimpleRecord` entries (e.g. `kind="decision"`).
- Explanation records are `ExplanationRecord` entries with `kind="explanation"`.
- Explanation payloads include a `decision_id` and human-readable text fields.

## Iteration Deliverable (PoC)
- Explanation payload structure.
- Helper for creating explanation records.
- Example and tests for storing and retrieving explanations.

## Implementation Plan
1. **Define explanation payload structure**
   - Minimal fields for decision linkage and summaries.
2. **Add creation helper**
   - Helper to create explanation records with `kind="explanation"`.
3. **Update examples and tests**
   - Minimal example and unit tests for explanation retrieval.
4. **Document usage**
   - Add README entry for interpretability records.

## Backward Compatibility
No backward compatibility impact; this introduces a new record type.

## Testing Strategy
- Unit test for explanation record creation and retrieval.
- Example demonstrating decision → explanation linkage.

## Related Requirements
This CIP addresses the following requirements:
- REQ-0006: Interpretability of Agent Decisions

## Implementation Status
- [x] Define explanation payload structure
- [x] Add creation helper
- [x] Update examples and tests
- [x] Document usage

## Progress Updates

### 2026-02-04
Iteration 1 complete. Explanation payload, helper, tests, and examples added. Tests passed. Iteration 2 planned. Next iteration should add interpretability artefacts on top of the explanation records.

After Iteration 1 explanations are human-readable, retrievable from shared data, and linked to decisions via separate records. The approach preserves the core record envelope while enabling multiple explanations per decision.

Gaps and follow-on needs:
- Define interpretability artefacts layered on top of explanation records (generation, summarisation, or aggregation).
- Consider guidance for explanation granularity and evidence conventions. We should define how detailed explanations should be (short rationales, full rationales, or multiple tiers) and what counts as evidence.

### 2026-02-06
Iteration 2 questions to support across scenarios (environment-agnostic):
- Which observation features most influenced an action?
- Is the agent pursuing its goal or reacting to other agents?
- Are actions consistent with the stated objective over time?
- What is the minimal evidence needed to justify an action?

These questions should be answerable without assuming a specific environment or observation schema.

## References
- None yet
