---
id: "2026-02-16_adapter-contract-dedup"
title: "Document adapter contract for state deduplication"
status: "Completed"
priority: "Medium"
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
- documentation
---

# Task: Document adapter contract for state deduplication

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Document the adapter contract for state deduplication. Adapters that support outcome deduplication must implement state lookup (state_hash -> outcome_id). Document how JSON, database, and stream adapters can fulfil this contract, and what optional methods or hooks the adapter interface requires.

## Acceptance Criteria

- [x] Adapter contract doc specifies: when dedup is expected, how state_hash is computed.
- [x] Contract describes optional vs required behaviour for adapters.
- [x] JSON: in-memory or sidecar index. DB: native indexes. Streams: medium-specific approach.
- [x] Contract is linked from data model spec and state-dedup-contract.

## Implementation Notes

- Add to docs/ or extend existing adapter documentation.
- Keep contract minimal; adapters that do not implement dedup can skip (no index, always create new outcomes).

## Related

- CIP: 0002
- PRs: N/A
- Documentation: State dedup contract, data model spec

## Progress Updates

### 2026-02-16
Task created. Part of REQ-0001/CIP-0002 iteration 2 backlog.

### 2026-02-21
Created `docs/adapter-contract.md` covering:
- Core interface (write, read, list, listen) with guarantees (append-only, immutable, ordered).
- Dedup extension (lookup_outcome_by_hash, index_outcome) — optional, adapters without them work transparently.
- Implementation guidance for in-memory, file-based (sidecar), database (native index), and stream (compaction/cache) backends.
- Custom adapter instructions (structural typing via Protocol).
- Linked from `docs/data-model-spec.md` references section.

### 2026-02-21
Updated `docs/adapter-contract.md` with:
- Collection-per-kind storage model (§2) — all adapters now use one collection/file per kind.
- MongoDB adapter section (§4.3) with collection layout and index guidance.
- Design decisions log (§6) documenting alternatives considered for storage layout, dedup default, index ownership, hash computation, and MongoDB `_id` strategy.
