---
id: "2026-02-16_initial-state-constant"
title: "Add initial_state constant for first environment outcome"
status: "Proposed"
priority: "Medium"
created: "2026-02-16"
last_updated: "2026-02-16"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- shared-data
- outcome
---

# Task: Add initial_state constant for first environment outcome

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Define a fixed ID `"initial_state"` for the first environment outcome (state before any agent acts). The first trace can use `from_id: "initial_state"` and `to_id: <first_real_outcome_id>`. No UUID generation needed; stable and easy to reference.

## Acceptance Criteria

- [ ] Constant or literal `"initial_state"` is defined and exported.
- [ ] Initial environment outcome uses this ID when written.
- [ ] Documentation or spec references the initial state convention.
- [ ] First trace correctly references `from_id: "initial_state"` when applicable.

## Implementation Notes

- Add to `doagent.records` or `doagent.core.shared_data` as `INITIAL_STATE_ID = "initial_state"`.
- Scenario/env run setup creates or references initial outcome with this id before first step.

## Related

- CIP: 0002
- PRs: N/A
- Documentation: Data model spec

## Progress Updates

### 2026-02-16
Task created.
