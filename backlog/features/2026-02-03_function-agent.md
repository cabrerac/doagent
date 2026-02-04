---
id: "2026-02-03_function-agent"
title: "Implement function-backed agent adapter"
status: "Completed"
priority: "High"
created: "2026-02-03"
last_updated: "2026-02-03"
category: "features"
related_cips:
- "0005"
owner: "Christian Cabrera"
dependencies:
- "2026-02-03_agent-interface"
tags:
- backlog
- model-agnostic
---

# Task: Implement function-backed agent adapter

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Implement a minimal agent adapter that wraps a callable for decision-making.

## Acceptance Criteria
- [x] Adapter accepts a callable and returns a decision response.
- [x] Adapter is compatible with the shared data model.

## Implementation Notes
Keep the adapter small and deterministic for tests.

## Related
- CIP: 0005
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-02-03
Task created.

### 2026-02-03
Added `FunctionAgent` with decision persistence to shared data.
