---
id: "2026-02-04_accountability-structure"
title: "Define accountability structure"
status: "Proposed"
priority: "High"
created: "2026-02-04"
last_updated: "2026-02-04"
category: "features"
related_cips:
- "0009"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- accountability
---
# Task: Define accountability structure

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Define an Accountability type (e.g. TypedDict) with optional owner, policy_id, responsibility_scope for use on the record envelope.

## Acceptance Criteria
- [ ] Accountability type is defined with optional owner, policy_id, responsibility_scope.
- [ ] Type is documented and exported from records.

## Implementation Notes
Keep the structure small and optional (total=False or all optional).

## Related
- CIP: 0009
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-02-04
Task created.
