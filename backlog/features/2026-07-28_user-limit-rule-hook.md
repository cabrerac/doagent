---
id: "2026-07-28_user-limit-rule-hook"
title: "Hook so users can supply their own limit rule"
status: "Ready"
priority: "High"
created: "2026-07-28"
last_updated: "2026-07-28"
category: "features"
related_cips:
- "0011"
owner: "Christian Cabrera"
dependencies:
- "2026-07-28_run-config-time-limits"
tags:
- backlog
- bounded-runs
- extensibility
---

# Task: Hook so users can supply their own limit rule

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Let users pass their own rule for stopping a run instead of the built-in numbers — for example a spending cap, a
per-agent quota, or a limit on how many model calls are made.

Follow the pattern the library already uses for `participation_registry` and `state_hash_fn`: a sensible default,
with an optional object accepted in session config. Keep it to one small protocol; this should not grow into a
framework.

Whichever rule decides to stop, the library writes the record. That is the reason for having the hook at all: a
timeout written in user code leaves nothing to inspect, while a library-side one is recorded the same way every time.

## Acceptance Criteria

- [ ] One small protocol defines a user-supplied limit rule.
- [ ] Session config accepts a user rule alongside the built-in numbers.
- [ ] A user rule that stops a run produces the same kind of record as the built-in limits.
- [ ] The built-in behaviour still applies when no rule is supplied.
- [ ] The protocol is documented where run configuration is described.

## Implementation Notes

`Session.from_config` already accepts `participation_registry` as a user-supplied object, so the shape and the naming
should mirror that.

Keep the protocol small — enough to ask "may this decision proceed?" and to be told what happened — rather than
exposing the internals of how limits are measured.

## Related

- CIP: [0011](../../cip/cip0011_llm-agents.md)
- Depends on: [2026-07-28_run-config-time-limits](./2026-07-28_run-config-time-limits.md)

## Progress Updates

### 2026-07-28

Task created when CIP-0011 was accepted. Depends on the built-in limits landing first.
