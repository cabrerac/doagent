---
id: "2026-02-16_run-api-level-config"
title: "High-level run API using logging level config"
status: "Completed"
priority: "Medium"
created: "2026-02-16"
last_updated: "2026-02-19"
category: "features"
related_cips:
- "0001"
owner: "Christian Cabrera"
dependencies:
- "2026-02-16_wire-records-to-level"
tags:
- backlog
- api
- validation
---

# Task: High-level run API using logging level config

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Ensure logging level config is available at the orchestration surface. Convenience run APIs (run_push_validation, run_gridworld_validation) accept RunConfig and wire it to RecordWriter.

## Acceptance Criteria
- [x] Convenience run APIs accept logging_level (0, 1, 2) as parameter or config.
- [x] Config passed to agents/scenarios flows to record writers (hooks).
- [ ] Gridworld and push validation examples demonstrate level config usage.
- [ ] Documentation shows how to run with different levels.

## Alternatives Considered

- **Scenario-specific run APIs as user surface:** User calls run_gridworld_validation directly. Simple, but couples user to specific scenarios.
- **Session API as user surface:** User creates a Session, wraps env, creates agents; records happen transparently. Decoupled from scenarios.

**Selected:** Session API (new task 2026-02-19_session-api). This task covers the internal wiring (run APIs accept config); the Session task covers the user-facing surface.

## Implementation Notes
- run_gridworld_validation and run_push_validation accept run_config and pass to RecordWriter.
- User-facing transparent API will be via Session (see 2026-02-19_session-api).

## Related
- CIP: 0001
- PRs: N/A
- Documentation: docs/library-boundaries.md, Examples, AGENTS.md
- Superseded by: 2026-02-19_session-api (for user-facing surface)

## Progress Updates

### 2026-02-16
Task created. Part of REQ-0001/CIP-0001 iteration 2 backlog.

### 2026-02-19
Internal wiring complete: both scenarios accept run_config, flow to RecordWriter. Marked complete. User-facing transparent API deferred to Session task.
