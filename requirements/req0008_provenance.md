---
id: "0008"
title: "System Wide Provenance"
status: "Implemented"
priority: "High"
created: "2026-01-22"
last_updated: "2026-03-19"
related_tenets:
- "provenance-and-accountability"
- "data-first-shared-model"
stakeholders:
- "system operators"
- "auditors"
- "end users"
tags:
- requirements
- provenance
---

# REQ-0008: System Wide Provenance

## Description
The system must provide end-to-end provenance for agent actions, data transformations, and decisions. It should be possible to trace outputs back to inputs, tools, and contributing agents in a way that supports audit and governance.

This requirement focuses on lineage: the data and decision history must be preserved and navigable.

**Why this matters**: Provenance makes traceability and audit possible across distributed systems.

**Who benefits**: Auditors, compliance teams, platform operators, and end users.

## Acceptance Criteria
- [x] Agent outputs can be traced to their inputs and influencing artefacts.
- [x] Provenance data is available for auditing across the system.
- [x] Decision chains can be reconstructed from stored records.

## Notes (Optional)
Retention policies and storage strategies are defined in CIPs.

## References
- **Related Tenets**: provenance-and-accountability, data-first-shared-model
- **External Links**: None

## Progress Updates

### 2026-01-22
Requirement drafted.

### 2026-02-21
CIP-0008 iteration 1 complete (4/4 items). Flat provenance attribution (`created_by`, `derived_from`, `used_tools`, `notes`) on every `SimpleRecord` envelope. `new_provenance()` helper builds attribution. Provenance populated automatically by `RecordWriter` at logging level >= 2. Trace records + provenance enable full decision chain reconstruction. Also addressed by CIP-0002 (shared data model).

### 2026-01-28
Analysis demo: provenance_walker.py walks derived_from chains backwards from any record. Demonstrates provenance as source of truth for "who created what from what." Full chain reconstruction from stored records validated.

### 2026-03-19
Requirement marked **Implemented**; follow-on provenance/trace automation remains on **CIP-0008**.
