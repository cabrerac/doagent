# DOAgent Adapter Contract

This document specifies the contract that `SharedDataAdapter` implementations must fulfil. It covers the core CRUD interface, the collection-per-kind storage model, the state deduplication extension, and guidance for different storage backends.

---

## 1. Core Interface

Every adapter implements the `SharedDataAdapter` protocol:

| Method | Signature | Required | Description |
|--------|-----------|----------|-------------|
| `write` | `(record: SimpleRecord) -> None` | Yes | Persist a record. |
| `read` | `(record_id: str) -> Optional[SimpleRecord]` | Yes | Retrieve a record by id. |
| `list` | `() -> Iterable[SimpleRecord]` | Yes | Return all records, ordered by timestamp. |
| `listen` | `(kind, *, actor, since, until) -> Iterable[SimpleRecord]` | Yes | Filter records by kind with optional actor/time constraints. |

**Guarantees:**
- `write` is append-only. Records are immutable once written.
- `read` returns `None` for unknown ids (no exceptions).
- `list` returns records sorted by timestamp across all kinds.
- `listen` filters are conjunctive (all specified constraints must match).

---

## 2. Collection-per-Kind Storage Model

All adapters store records in **one collection per record kind** (`agent_update`, `outcome`, `trace`, etc.). This layout:

- Makes `listen(kind=...)` efficient (reads only the relevant collection/file).
- Aligns all three adapter types (in-memory, file, MongoDB) to the same conceptual model.
- Mirrors how document databases (MongoDB) naturally organise data.

| Adapter | Kind mapping |
|---------|-------------|
| **InMemorySharedData** | `Dict[kind, Dict[id, SimpleRecord]]` — one nested dict per kind |
| **FileSharedData** | `<directory>/<kind>.jsonl` — one JSONL file per kind |
| **MongoSharedData** | One MongoDB collection per kind |

**Design alternative considered:** Single flat store (one dict / one file / one collection for all records). This was the original design. Rejected because it makes kind-scoped queries (`listen`) O(n) over all records, and does not scale when different kinds have different query patterns and indexes.

---

## 3. State Deduplication Extension

Adapters that support environment outcome deduplication implement two additional methods. All three provided adapters implement these.

| Method | Signature | Required | Description |
|--------|-----------|----------|-------------|
| `lookup_outcome_by_hash` | `(state_hash: str) -> Optional[str]` | No | Return the outcome record id for an already-seen state hash, or `None`. |
| `index_outcome` | `(state_hash: str, outcome_id: str) -> None` | No | Store a `state_hash → outcome_id` mapping. |

### 3.1 When Dedup Activates

Deduplication is **on by default** (`Session` uses `default_state_hash`). The flow:

1. `RecordWriter` calls `state_hash_fn(payload)` to compute the hash.
2. `RecordWriter` calls `adapter.lookup_outcome_by_hash(state_hash)`.
3. If the adapter returns an existing id, no new outcome is written — the trace reuses the existing outcome.
4. If not found, the outcome is written and `adapter.index_outcome(state_hash, outcome_id)` is called.

### 3.2 Hash Computation

The adapter does **not** compute the hash. The hash function is provided by the library (`default_state_hash` = SHA-256 of canonical JSON) or overridden by the user. The adapter only stores and looks up hash-to-id mappings.

### 3.3 Fallback Behaviour

Adapters that do not implement `lookup_outcome_by_hash` / `index_outcome` return `None` / no-op respectively. The `RecordWriter` checks for method presence via `getattr` before calling, so custom adapters without these methods work without error.

---

## 4. Implementation Guidance by Backend

### 4.1 In-Memory (`InMemorySharedData`)

- **Collections:** `Dict[kind, Dict[id, SimpleRecord]]`.
- **Insertion order:** Maintained via a separate `_insertion_order` list (for `list()`).
- **Id lookup:** `_id_to_kind` reverse index for O(1) `read()`.
- **Dedup index:** `Dict[str, str]` mapping `state_hash → outcome_id`.
- **Lifetime:** Single run. Lost on garbage collection.
- This is the reference implementation.

### 4.2 File-Based (`FileSharedData`)

- **Layout:** One `<kind>.jsonl` file per kind inside a directory.
- **Write:** Append to `<kind>.jsonl`.
- **Listen:** Read only `<kind>.jsonl` — no scanning of other files.
- **List:** Merge all `*.jsonl` files, sort by timestamp.
- **Read:** Scan all files until the id is found.
- **Dedup index:** In-memory `Dict[str, str]` for the adapter's lifetime.

**Design alternative considered:** Single `records.jsonl` file. This was the original design. Rejected to align with the collection-per-kind model and to make `listen()` efficient without scanning unrelated records.

### 4.3 MongoDB (`MongoSharedData`)

- **Layout:** One MongoDB collection per kind (`agent_update`, `outcome`, `trace`).
- **Dedup index:** `_state_index` collection with `state_hash` → `outcome_id` documents.
- **Indexes:** `ensure_indexes()` creates recommended indexes (`_record_id` unique, `actor`, `timestamp`, `state_hash` unique).
- **Dependency:** Requires `pymongo` (optional; import guarded by try/except).
- **Listen filters:** Translated to native MongoDB queries for efficient server-side filtering.

### 4.4 Streams (Kafka, Redis Streams)

- Records: published to a topic/stream.
- Dedup index: medium-specific. Options:
  - Compact log with hash as key (Kafka compaction).
  - Redis hash map for lookup.
  - External cache (e.g. Redis `GET`/`SET` for hash lookups alongside the stream).
- Dedup may be impractical for high-throughput streams; adapters can skip it.

---

## 5. Custom Adapters

To create a custom adapter:

1. Implement the four core methods (`write`, `read`, `list`, `listen`).
2. Optionally implement `lookup_outcome_by_hash` and `index_outcome` for dedup.
3. The adapter is structurally typed (Python `Protocol`) — no base class inheritance required.
4. Follow the collection-per-kind pattern if applicable to your storage backend.

---

## 6. Design Decisions Log

| Decision | Chosen | Alternative | Rationale |
|----------|--------|-------------|-----------|
| Storage layout | Collection-per-kind | Single flat store | Efficient kind-scoped queries; aligns in-memory, file, and DB adapters |
| Dedup default | On (`default_state_hash`) | Opt-in | Trace graph is a core concept; linear chains are a degenerate case |
| Dedup index location | Adapter-owned | RecordWriter-owned | Adapters control their storage medium; DB adapters use native indexes |
| Default hash scope | State fields only (`observations`, `done`) | Full payload (incl. round, actions, rewards) | Same physical state at different rounds must deduplicate; transition/temporal data is not state |
| Hash computation | Library/user-provided, not adapter | Adapter-computed | Separation of concerns; adapter only stores mappings |
| MongoDB `_id` | Use Mongo's auto `_id` + store `_record_id` | Use record `id` as `_id` | Avoids conflicts with Mongo's `ObjectId` convention |

---

## References

- [Data Model Spec](data-model-spec.md) — record envelope, kinds, dedup contract (§9).
- [Library Boundaries](library-boundaries.md) — user vs library responsibilities.
- CIP-0002: Shared Data Model as Agent Interface.
