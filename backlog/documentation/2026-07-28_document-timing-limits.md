---
id: "2026-07-28_document-timing-limits"
title: "Document timing limits and the user limit hook"
status: "Ready"
priority: "Medium"
created: "2026-07-28"
last_updated: "2026-07-28"
category: "documentation"
related_cips:
- "0011"
owner: "Christian Cabrera"
dependencies:
- "2026-07-28_run-config-time-limits"
- "2026-07-28_user-limit-rule-hook"
tags:
- backlog
- documentation
- bounded-runs
---

# Task: Document timing limits and the user limit hook

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Write down how the limits work once they exist: the two numbers in `run_config`, what happens when a limit is reached,
and how to supply your own rule instead.

`docs/library-boundaries.md` needs one extra line. It currently says the user sets run configuration "once (e.g.
logging level)" and controls when things happen. Timing limits fit that split rather than change it — the user picks
the numbers and the library enforces them — so the doc should simply list timing limits as something run
configuration can include.

## Acceptance Criteria

- [ ] Run configuration docs cover both limits and their defaults.
- [ ] The docs say a cut-short decision appears as `choice.status: "error"` with detail in `choice.error`.
- [ ] The user limit hook is documented with a short example.
- [ ] `docs/library-boundaries.md` lists timing limits as part of run configuration.
- [ ] No claim that the library takes timing control away from the user.

## Implementation Notes

Keep this small and plain. The point users need is: your run will always finish, you choose the numbers, and if a
decision was cut short you can see it in the records.

## Related

- CIP: [0011](../../cip/cip0011_llm-agents.md)
- Depends on: [2026-07-28_run-config-time-limits](../features/2026-07-28_run-config-time-limits.md),
  [2026-07-28_user-limit-rule-hook](../features/2026-07-28_user-limit-rule-hook.md)
- Documentation: `docs/library-boundaries.md`, `docs/data-model-spec.md`

## Progress Updates

### 2026-07-28

Task created when CIP-0011 was accepted. Kept as documentation rather than folded into the code tasks, since it
touches the boundaries doc.
