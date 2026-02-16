---
id: "2026-02-16_trace-schema"
title: "Formalise trace schema (from_id, to_id, enabled_by_id, metadata)"
status: "Proposed"
priority: "High"
created: "2026-02-16"
last_updated: "2026-02-16"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies:
- "2026-02-16_data-model-spec"
tags:
- backlog
- trace
- shared-data
---

# Task: Formalise trace schema (from_id, to_id, enabled_by_id, metadata)

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Update the trace record schema to support the state-transition graph model. Traces link environment outcomes (states) and agent updates (enablers). Each trace has:
- `from_id`: environment_outcome (state before)
- `to_id`: environment_outcome (state after)
- `enabled_by_id`: agent_update that caused the transition
- Metadata on trace: `round`, `timestamp` (temporal info lives on trace, not on outcome)

## Acceptance Criteria

- [ ] Trace record schema includes `from_id`, `to_id`, `enabled_by_id`.
- [ ] Trace carries `round` and `timestamp` (or equivalent) for temporal context.
- [ ] Schema is documented (typed or in spec).
- [ ] Existing trace creation is updated to use new schema where applicable.

## Implementation Notes

- Trace payload or envelope fields; prefer consistent placement across record kinds.
- Outcome records stay "pure state"; temporal metadata is on trace.

## Related

- CIP: 0002
- PRs: N/A
- Documentation: Data model spec

## Progress Updates

### 2026-02-16
Task created.
