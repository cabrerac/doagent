---
id: "2026-02-04_explanation-helper"
title: "Add helper for explanation records"
status: "Completed"
priority: "High"
created: "2026-02-04"
last_updated: "2026-02-04"
category: "features"
related_cips:
- "0006"
owner: "Christian Cabrera"
dependencies:
- "2026-02-04_interpretability-payload"
tags:
- backlog
- interpretability
---

# Task: Add helper for explanation records

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Add a helper to create explanation records with `kind="explanation"`.

## Acceptance Criteria
- [x] Helper accepts decision linkage and summary fields.
- [x] Helper returns a `SimpleRecord` ready for shared data.

## Implementation Notes
Use the existing record envelope and keep parameters minimal.

## Related
- CIP: 0006
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-02-04
Task created.

### 2026-02-04
Added `new_explanation_record` helper.
