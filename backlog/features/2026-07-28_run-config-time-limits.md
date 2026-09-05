---
id: "2026-07-28_run-config-time-limits"
title: "Time limits for a decision and for a whole run"
status: "Ready"
priority: "High"
created: "2026-07-28"
last_updated: "2026-07-28"
category: "features"
related_cips:
- "0011"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- bounded-runs
- run-config
---

# Task: Time limits for a decision and for a whole run

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Add two limits to `run_config`: how long a single decision may take, and how long a whole run may take. Enforce them
where the session already wraps decisions, so any decision engine is covered, not only LLM policies.

When a decision passes its limit, record it as `choice.status: "error"` with the detail in `choice.error`. No new
status value and no change to the record format. When a run passes its limit, stop in a controlled way so the run
still finishes and its records can be read back.

Defaults must keep today's behaviour, so existing runs and tests are unaffected.

## Acceptance Criteria

- [ ] `run_config` accepts a limit for a single decision and a limit for a whole run.
- [ ] A policy that runs past its limit produces an error decision, and the run continues or stops cleanly.
- [ ] A run that passes the whole-run limit stops in a controlled way and its records are inspectable.
- [ ] The cut-short reason is readable in `choice.error`.
- [ ] Defaults leave current behaviour unchanged; existing tests pass untouched.
- [ ] No provider-specific code is added to the library.

## Implementation Notes

The limit belongs where decisions already pass through the library, so the record is written in one place. Reusing
`choice.status: "error"` was a deliberate choice in CIP-0011 to avoid touching the data model, which CIP-0002 owns.

Sequential decisions make the whole-run limit simple to measure. If decisions later run concurrently, that
measurement changes — noted as a future item in CIP-0011, not handled here.

## Related

- CIP: [0011](../../cip/cip0011_llm-agents.md)
- Documentation: `docs/data-model-spec.md` (choice shape), `docs/library-boundaries.md`

## Progress Updates

### 2026-07-28

Task created when CIP-0011 was accepted. First step of the plan; the user hook (separate task) builds on this.
