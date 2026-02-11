---
id: "2026-02-04_accountability-tests-docs"
title: "Add accountability helper, tests, and docs"
status: "Completed"
priority: "Medium"
created: "2026-02-04"
last_updated: "2026-02-11"
category: "features"
related_cips:
- "0009"
owner: "Christian Cabrera"
dependencies:
- "2026-02-04_accountability-envelope"
tags:
- backlog
- accountability
- tests
---
# Task: Add accountability helper, tests, and docs

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Add optional helper to build accountability dict, example and unit tests for records with accountability, and README note.

## Acceptance Criteria
- [x] Optional helper to build accountability (owner, policy_id, responsibility_scope) for use with new_record.
- [x] Tests cover record creation with accountability and round-trip.
- [x] README includes short note on accountability and API.

## Implementation Notes
Use unittest; keep example minimal.

## Related
- CIP: 0009
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-02-04
Task created.

### 2026-02-11
Verified implemented. `new_accountability` helper in `doagent.records`, `test_accountability.py` with 4 tests (helper + round-trip), `examples/features/accountability_usage.py`, README Accountability section. Marked Completed.
