---
id: "2026-02-05_validation-baseline-comparison"
title: "Add baseline (non-data-oriented) comparison run"
status: "Completed"
priority: "Medium"
created: "2026-02-05"
last_updated: "2026-02-05"
category: "features"
related_cips:
- "0010"
owner: "Christian Cabrera"
dependencies:
- "2026-02-05_validation-push-env-interface"
- "2026-02-05_validation-push-agents"
tags:
- backlog
- validation
- games
- benchmarking
---
# Task: Add baseline (non-data-oriented) comparison run

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Run the same simple push scenario with data-oriented writes disabled to compare overhead (runtime and output size) against the DOAgent record pipeline.

## Acceptance Criteria
- [x] Baseline run uses the same policies and environment without shared-data writes.
- [x] Baseline collects timing and output size metrics.
- [x] Comparison results are recorded in a summary artifact.

## Implementation Notes
Prefer a no-op shared data adapter or a flag that bypasses record writes.

## Related
- CIP: 0010
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-02-05
Task created.

### 2026-02-05
Added NoOpSharedData adapter and baseline timing helper; scenario wiring pending.

### 2026-02-05
Scenario runner added; baseline can reuse NoOpSharedData for overhead comparison.

### 2026-02-05
Summary artifact still pending.

### 2026-02-05
Summary artifact written by push_validation example.
