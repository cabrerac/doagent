---
id: "2026-02-16_state-lookup-index"
title: "Implement state lookup index for JSON/file adapter"
status: "Proposed"
priority: "High"
created: "2026-02-16"
last_updated: "2026-02-16"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies:
- "2026-02-16_state-dedup-contract"
tags:
- backlog
- adapter
- shared-data
---

# Task: Implement state lookup index for JSON/file adapter

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Implement the state_hash to outcome_id index for the JSON/file adapter so that environment outcomes can be deduplicated. When writing an outcome, compute state hash, check if equivalent state exists, and either reuse existing outcome id or create new and index it. Adapter maintains index (in-memory or sidecar file) for the duration of the run.

## Acceptance Criteria

- [ ] JSON/file adapter maintains state_hash -> outcome_id index.
- [ ] On outcome write: compute hash, lookup; if exists reuse id, else create and index.
- [ ] Trace to_id correctly references reused outcome when state is equivalent.
- [ ] Tests verify deduplication and trace graph construction.

## Implementation Notes

- In-memory dict for single-run usage; optionally persist sidecar (e.g. outcome_index.json) if needed.
- Hash input: canonical serialisation of outcome payload (or scenario-defined subset).
- Integrate with existing FileSharedData or equivalent adapter.

## Related

- CIP: 0002
- PRs: N/A
- Documentation: State dedup contract, adapter contract

## Progress Updates

### 2026-02-16
Task created. Part of REQ-0001/CIP-0002 iteration 2 backlog.
