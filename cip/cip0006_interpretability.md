---
author: "Christian Cabrera"
created: "2026-02-04"
id: "0006"
last_updated: "2026-01-28"
status: "Implemented"
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
- [ ] In Progress - Actively being implemented
- [x] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

**Note:** **Implemented** here means the **scoped deliverables below (iterations 1–2) are in the codebase**. Remaining interpretability ideas (narrative summaries, joint graph+text views, Q/A bundles, export naming improvements, etc.) are **explicitly out of scope** for this CIP; they are tracked as **future iterations** in `backlog/features/2026-03-19_explanations-storage-doc.md` and may become a **new CIP or CIP-0006 iteration 3** when requirements are written. That is normal: a CIP closes its agreed scope; follow-ons get their own backlog/CIP entries.

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

### Iteration 1 (shared-data explanation records)
- [x] Define explanation payload structure
- [x] Add creation helper
- [x] Update examples and tests
- [x] Document usage

### Iteration 2 (`doagent.analysis.interpretability`)
- [x] `build_atomic_explanations(record_id, run_id, output_base=None)` with Level 1/2 units
- [x] `render_atomic_explanation_text` for stable human-readable lines
- [x] Tests (`tests/test_analysis_interpretability.py`) and user docs (`guides/interpreting-analysis.md`, README, demos/notebooks)

### Deferred (future iterations — does not block Implemented)
- Advanced interpretability artefacts and presentation upgrades: see **Advanced interpretability artefacts (deferred)** in `backlog/features/2026-03-19_explanations-storage-doc.md`.

## Iteration 2 Plan: doagent.analysis.interpretability

Promote analysis capabilities into a first-class library module. Iteration 2 adds `doagent.analysis` with property-based submodules; interpretability is one of four.

**Deliverable**: `doagent.analysis.interpretability` submodule
- `build_atomic_explanations(record_id, run_id, output_base=None)` — build transition-level atomic explanations for a record
- Minimal initially; extensible for summarisation, aggregation, and evidence conventions
- Records source: Path, SharedDataAdapter, or dict of record lists
- Environment-agnostic: works with any DOAgent run output

**Design**: Group analyses by the property they enable. User imports `from doagent.analysis import interpretability`. New approaches (e.g. explanation summarisation, multi-tier rationales) added as functions in this submodule.

**Related backlog**: 2026-03-04_analysis-module-library

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

### 2026-03-04
Iteration 2 plan added: `doagent.analysis.interpretability` submodule. See Iteration 2 Plan section.

### 2026-01-28
Moved CIP to **Implemented**: iterations 1–2 deliverables are complete (`explanation` records + `doagent.analysis.interpretability` atomic units). Backlog `2026-03-04_analysis-module-library` is **Completed**. Follow-on interpretability work remains documented as **deferred** in `2026-03-19_explanations-storage-doc.md` (not part of this CIP’s scope). **Closed** (verification sign-off) can follow a formal REQ-0006 check if the project requires it.

Early validation (for context): analysis demos (`provenance_walker`, causal attribution) showed external interpretability from recorded data before the library module landed; iteration 2 consolidated interpretability under `doagent.analysis`.

## References
- None yet
