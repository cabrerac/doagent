---
id: "2026-02-04_accountability-envelope"
title: "Extend record envelope and new_record for accountability"
status: "Proposed"
priority: "High"
created: "2026-02-04"
last_updated: "2026-02-04"
category: "features"
related_cips:
- "0009"
owner: "Christian Cabrera"
dependencies:
- "2026-02-04_accountability-structure"
tags:
- backlog
- accountability
---
# Task: Extend record envelope and new_record for accountability

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Add optional accountability field to SimpleRecord and update new_record to accept and pass through optional accountability. Ensure adapters (in-memory, file) handle the new field.

## Acceptance Criteria
- [ ] SimpleRecord has optional accountability field with a safe default.
- [ ] new_record accepts optional accountability and sets it on the record.
- [ ] Existing record creation paths remain valid (backward compatible).

## Implementation Notes
Default accountability to empty dict or equivalent; update serialisation (e.g. asdict) if needed for file adapter.

## Related
- CIP: 0009
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-02-04
Task created.
