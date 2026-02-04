---
id: "2026-02-04_provenance-helper"
title: "Add provenance helper"
status: "Completed"
priority: "High"
created: "2026-02-04"
last_updated: "2026-02-04"
category: "features"
related_cips:
- "0008"
owner: "Christian Cabrera"
dependencies:
- "2026-02-04_provenance-semantics-docs"
tags:
- backlog
- provenance
---
# Task: Add provenance helper

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Add a helper to build a Contribution or Provenance dict from (agent, sources, tools, notes, optional id) for use with new_record.

## Acceptance Criteria
- [ ] Helper accepts agent, sources, tools, optional notes and contribution id.
- [ ] Helper returns a structure suitable for record provenance (Contribution or Provenance with one contribution).

## Implementation Notes
Keep the helper small; support one contribution per call; callers can build a list for multiple agents if needed.

## Related
- CIP: 0008
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-02-04
Task created.

### 2026-02-04
Added `new_provenance` in `doagent.records`.
