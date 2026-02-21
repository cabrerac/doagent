---
id: "2026-02-16_state-lookup-index"
title: "Implement state lookup index for JSON/file adapter"
status: "Completed"
priority: "High"
created: "2026-02-16"
last_updated: "2026-02-21"
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

- [x] JSON/file adapter maintains state_hash -> outcome_id index.
- [x] On outcome write: compute hash, lookup; if exists reuse id, else create and index.
- [x] Trace to_id correctly references reused outcome when state is equivalent.
- [x] Tests verify deduplication and trace graph construction.

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

### 2026-02-21
Implemented state lookup index for both adapters:
- `InMemorySharedData`: dedup index (`Dict[str, str]`) added with `lookup_outcome_by_hash` and `index_outcome` methods (implemented in state-dedup-contract task).
- `FileSharedData`: same in-memory dict pattern added. Lives for adapter lifetime (single run).
- `RecordWriter._dedup_or_write_outcome()` performs the full lookup → reuse/create → index flow.
- `Session` accepts `state_hash_fn` and passes it to `RecordWriter`.
- Dedup tests covered in the tests-trace-dedup task.
- All 49 existing tests pass.
