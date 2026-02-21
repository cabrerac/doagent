---
id: "2026-02-21_collection-per-kind-and-mongo-adapter"
title: "Collection-per-kind storage refactor and MongoDB adapter"
status: "Completed"
priority: "High"
created: "2026-02-21"
last_updated: "2026-02-21"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies:
- "2026-02-16_state-dedup-contract"
- "2026-02-16_adapter-contract-dedup"
tags:
- backlog
- adapter
- mongodb
- architecture
---

# Task: Collection-per-kind storage refactor and MongoDB adapter

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Refactor all shared data adapters to use a collection-per-kind storage model (one collection/file per record kind). Add a MongoDB adapter. Make state deduplication on-by-default.

Three changes bundled as one coherent architectural shift:
1. **Collection-per-kind**: `InMemorySharedData` uses nested dicts keyed by kind; `FileSharedData` stores one `<kind>.jsonl` per kind in a directory; `MongoSharedData` uses one collection per kind.
2. **Dedup on-by-default**: `Session` uses `default_state_hash` unless explicitly overridden.
3. **MongoSharedData**: New adapter using `pymongo` (optional dependency) with native query support and `_state_index` collection.

## Acceptance Criteria

- [x] `InMemorySharedData` uses `Dict[kind, Dict[id, SimpleRecord]]`.
- [x] `FileSharedData` accepts a directory path and writes `<kind>.jsonl` files.
- [x] `MongoSharedData` stores records in per-kind MongoDB collections.
- [x] `Session` uses `default_state_hash` by default; `state_hash_fn=None` opts out.
- [x] All existing tests pass with refactored adapters.
- [x] MongoDB adapter has dedicated tests (via `mongomock`).
- [x] Design alternatives documented in adapter contract.

## Implementation Notes

### Design alternatives considered

| Decision | Chosen | Alternative | Rationale |
|----------|--------|-------------|-----------|
| Storage layout | Collection-per-kind | Single flat store | Efficient kind-scoped queries; aligns all adapters |
| Dedup default | On (`default_state_hash`) | Opt-in | Trace graph is a core concept; linear chains are degenerate |
| `FileSharedData` input | Directory path | Single file path | Aligns with collection-per-kind; one file per kind |
| MongoDB `_id` | Auto `_id` + `_record_id` | Record `id` as `_id` | Avoids `ObjectId` conflicts |
| `pymongo` dependency | Optional (try/except) | Required | Not all users need MongoDB |

## Related

- CIP: 0002
- PRs: N/A
- Documentation: Adapter contract, data model spec

## Progress Updates

### 2026-02-21
Task created and completed in same session:
- `InMemorySharedData`: refactored to `_collections` dict-of-dicts + `_insertion_order` list + `_id_to_kind` reverse index.
- `FileSharedData`: now accepts directory, writes `<kind>.jsonl` files. `listen()` reads only the relevant file. `list()` merges all files sorted by timestamp.
- `MongoSharedData`: new adapter in `doagent/core/mongo_shared_data.py`. Per-kind collections, `_state_index` collection for dedup, `ensure_indexes()` for recommended DB indexes.
- `Session.__init__`: uses sentinel `_DEDUP_DEFAULT` to distinguish "not provided" (→ `default_state_hash`) from explicit `None` (→ no dedup).
- `output_bytes_from_path`: updated to handle directories (sum of file sizes).
- Tests updated: `FileSharedData` callers now pass directory paths. 11 new MongoDB tests via `mongomock`.
- Total: 72 passed, 3 skipped.
