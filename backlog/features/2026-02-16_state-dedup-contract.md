---
id: "2026-02-16_state-dedup-contract"
title: "Define state equivalence and deduplication contract"
status: "Proposed"
priority: "High"
created: "2026-02-16"
last_updated: "2026-02-16"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies:
- "2026-02-16_data-model-spec"
tags:
- backlog
- shared-data
- adapter
---

# Task: Define state equivalence and deduplication contract

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Define the contract for state equivalence and outcome deduplication. When recording an environment outcome, the adapter checks if an equivalent state already exists (via hash). If yes, `to_id` points to the existing outcome; if no, create new outcome and index it. This enables traces to form a graph of states and transitions.

- **Equivalence:** Hash of the environment state (scenario-defined what gets hashed)
- **Index:** `state_hash → outcome_id`; adapter owns implementation
- **Metadata:** On trace, not on outcome (outcomes stay pure state)

## Acceptance Criteria

- [ ] Contract is documented: when to deduplicate, how state is hashed.
- [ ] Scenario/domain can influence what is included in hash (or default is documented).
- [ ] Adapter interface or contract specifies that adapters implementing dedup must maintain `state_hash → outcome_id` index.
- [ ] Write flow is documented: check existence → reuse or create → write trace.

## Implementation Notes

- Document in data model spec or adapter contract.
- Default: hash of canonical serialisation of outcome payload (or configurable subset).
- Adapters: JSON builds in-memory or sidecar index; DB uses native indexes; streams use what the medium offers.

## Related

- CIP: 0002
- PRs: N/A
- Documentation: Data model spec, adapter contract

## Progress Updates

### 2026-02-16
Task created.
