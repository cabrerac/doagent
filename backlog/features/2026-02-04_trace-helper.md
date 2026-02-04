---
id: "2026-02-04_trace-helper"
title: "Add helper for trace records"
status: "Completed"
priority: "High"
created: "2026-02-04"
last_updated: "2026-02-04"
category: "features"
related_cips:
- "0007"
owner: "Christian Cabrera"
dependencies:
- "2026-02-04_traceability-payload"
tags:
- backlog
- traceability
---

# Task: Add helper for trace records

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Add a helper to create trace records with `kind="trace"`.

## Acceptance Criteria
- [x] Helper accepts `from_id`, `to_id`, `relation`.
- [x] Optional fields are supported and preserved.

## Implementation Notes
Keep helper small and consistent with other record helpers.

## Related
- CIP: 0007
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-02-04
Task created.

### 2026-02-04
Added `new_trace_record` helper.
