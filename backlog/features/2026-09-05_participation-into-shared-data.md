---
id: "2026-09-05_participation-into-shared-data"
title: "Write participation events into the shared data model"
status: "Completed"
priority: "High"
created: "2026-09-05"
last_updated: "2026-09-05"
category: "features"
related_cips:
- "0004"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- openness
- shared-data
---

# Task: Write participation events into the shared data model

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

CIP-0004's blocking item: join, leave, and capability advertisement must be inspectable records, not only entries in
the in-memory registry. `Session.register_participant` / `deregister_participant` keep updating the registry and also
append a `SimpleRecord` of kind `participation` through the configured shared-data adapter.

The live registry stays the per-run index of who is in. The event log is what `inspect("participation")` reads. File
and Mongo adapters persist that log as they do any other kind (`participation.jsonl` / a `participation` collection).
Replaying events into the registry after a restart is a later CIP-0004 item.

## Acceptance Criteria

- [x] `register_participant` writes a `participation` record with `event: "join"` (capabilities, resource limits,
      metadata in the payload) and still updates the registry.
- [x] `deregister_participant` writes a `participation` record with `event: "leave"` and still updates the registry.
- [x] `session.inspect("participation")` returns those records.
- [x] Events are written at every logging level when participation is enabled. Envelope provenance / accountability
      follow Level 1+ like other records.
- [x] File persist the events via the existing adapter (`participation.jsonl`). Mongo uses the same write path (not
      separately exercised). NoOp discards them.
- [x] Existing registry tests still pass; new tests cover inspectability, file persist, and logging levels.

## Implementation Notes

Approach A (agreed 2026-09-05): new kind `participation`; keep `ParticipationRecord` as the registry DTO; dual-write
from Session. Do not reuse `agent_update`. Do not make the registry a replay view in this task.

## Related

- CIP: [0004](../../cip/cip0004_open-participation.md)
- Documentation: `docs/data-model-spec.md` (§3.3 participation)
- Tests: `tests/test_session.py` (register/deregister inspect, file persist, logging levels)

## Progress Updates

### 2026-09-05

Task created. Approach A agreed; docs and CIP note landed first. Code and tests follow in small verified steps.

### 2026-09-05 (later)

Implemented dual-write via `RecordWriter.on_participation`. Tests passed (inspect, `participation.jsonl`, levels 0–2).
Marked complete. Replay of live membership after restart remains on CIP-0004 as a future iteration.
