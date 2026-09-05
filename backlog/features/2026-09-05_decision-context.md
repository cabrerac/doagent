---
id: "2026-09-05_decision-context"
title: "session.decision_context for kinds, last N, and summarise"
status: "Completed"
priority: "High"
created: "2026-09-05"
last_updated: "2026-09-05"
category: "features"
related_cips:
- "0002"
- "0003"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- shared-data
---

# Task: session.decision_context for kinds, last N, and summarise

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Agents need a named way to get what they may use to decide. Not `memory` (that
sounds like choosing what to keep). `decision_context` reads the same visible
records, then optionally filters by kind(s), keeps the last N, and/or runs a
user summarise function.

## Acceptance Criteria

- [x] `session.decision_context(agent_id, kinds=..., last_n=..., summarise=...)`.
- [x] Same visibility as `visible_records`.
- [x] Gridworld demo uses it to build the shared map.

## Implementation Notes

`summarise` is a callable. The library does not invent a text summary.

## Related

- CIP: [0002](../../cip/cip0002_shared-data-model.md)
- Tests: `tests/test_session.py`

## Progress Updates

### 2026-09-05

Implemented. Tests passed. Marked complete.
