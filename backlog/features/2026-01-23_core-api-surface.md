---
id: "2026-01-23_core-api-surface"
title: "Design core API surface for CIP-0001"
status: "Completed"
priority: "High"
created: "2026-01-23"
last_updated: "2026-02-02"
category: "features"
related_cips:
- "0001"
owner: "Christian Cabrera"
dependencies:
- "2026-01-23_library-boundaries"
tags:
- backlog
- library
- api
---

# Task: Design core API surface for CIP-0001

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Design the minimal core API surface for the library, covering shared data adapters, agent adapters, and coordination hooks.

## Acceptance Criteria
- [ ] Core API primitives are listed with clear responsibilities.
- [ ] API design is aligned with modular adoption goals.

## Implementation Notes
Keep the API minimal and composable; avoid system-level assumptions.

## Related
- CIP: 0001
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-01-23
Task created.

### 2026-02-02
Set to In Progress. Drafting the minimal API surface first.

### 2026-02-02
Draft API primitives:
- `SimpleRecord` envelope (id, timestamp, actor, kind, payload, provenance).
- `SharedDataAdapter` protocol: `write`, `read`, `list`, `listen`.
- `InMemorySharedData` adapter.
- `AgentAdapter` protocol: `write`, `read`, `listen`.
- `StubAgent` adapter plus `new_record` helper.

### 2026-02-02
Implementation is now under `doagent.core` with interfaces kept internal.

### 2026-02-02
Updated records naming and user-facing modules (`doagent.core`, `doagent.records`).
