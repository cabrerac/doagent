---
id: "2026-07-28_budget-in-decision-request"
title: "Show the remaining budget in the decision request"
status: "Ready"
priority: "Medium"
created: "2026-07-28"
last_updated: "2026-07-28"
category: "features"
related_cips:
- "0011"
- "0005"
owner: "Christian Cabrera"
dependencies:
- "2026-07-28_run-config-time-limits"
tags:
- backlog
- bounded-runs
- temporal-analysis
---

# Task: Show the remaining budget in the decision request

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Include how much time or budget is left in the decision request, so a policy can choose to answer quickly or to think
longer.

Without this, only a hard cut-off is possible: the agent never knows it is under pressure, so it cannot adapt. With
it, the time budget becomes something agents can reason about, which is what makes the react-versus-reflect
comparison possible later.

The field is optional. Policies that ignore it keep working exactly as before.

## Acceptance Criteria

- [ ] The decision request carries the remaining time or budget.
- [ ] A policy can read it and change its behaviour based on it.
- [ ] Policies that ignore the field behave exactly as before.
- [ ] The addition stays consistent with the request and response payloads defined in CIP-0005.
- [ ] A test shows a policy answering differently under a tight budget than under a loose one.

## Implementation Notes

This touches the decision request, which CIP-0005 owns, so the field name and shape must fit the existing
`DecisionRequest` rather than sitting beside it.

The experiments that use this — comparing behaviour across budgets — belong to CIP-0010, not here. This task only
makes the budget visible.

## Related

- CIP: [0011](../../cip/cip0011_llm-agents.md), [0005](./../../cip/cip0005_model-agnostic-agents.md)
- Depends on: [2026-07-28_run-config-time-limits](./2026-07-28_run-config-time-limits.md)
- Documentation: `docs/data-model-spec.md`

## Progress Updates

### 2026-07-28

Task created when CIP-0011 was accepted. Came out of the react-versus-reflect discussion: a hard cut-off alone cannot
support that study.
