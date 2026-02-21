---
id: "2026-02-16_env-outcome-structure"
title: "Formalise environment_outcome payload (reward, env_status)"
status: "Completed"
priority: "Medium"
created: "2026-02-16"
last_updated: "2026-02-21"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies:
- "2026-02-16_data-model-spec"
tags:
- backlog
- shared-data
- outcome
---

# Task: Formalise environment_outcome payload (reward, env_status)

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Formalise the environment_outcome record structure as a general form that works across domains. Envelope is fixed; payload has domain-specific content. Document optional common slots: reward(s), env_status (observations, done, etc.). The payload remains flexible for different scenarios.

## Acceptance Criteria

- [x] environment_outcome payload structure is documented.
- [x] Common optional slots (reward, env_status, actions) are described.
- [x] Gridworld and push outcomes align with the documented structure.
- [x] Schema supports different domains without imposing rigid schema on payload.

## Implementation Notes

- Document in data model spec. Envelope: actor, kind, id, provenance, accountability, timestamp.
- Payload: open key-value; recommend reward, env_status as optional top-level keys.
- Existing validation scenarios (gridworld, push) may need minor payload reshapes to match.

## Related

- CIP: 0002
- PRs: N/A
- Documentation: Data model spec

## Progress Updates

### 2026-02-16
Task created.

### 2026-02-21
Formalised outcome payload structure:
- Expanded `docs/data-model-spec.md` §4.1 with a recommended key table: `observations` and `done` (state), `rewards` and `actions` (transition), `round` (temporal). Added category semantics for dedup alignment.
- Added optional `done` parameter to `RecordWriter.on_outcome_and_traces()` — termination flags are now recorded in the outcome payload.
- `WrappedEnv.step()` passes `done` from the step adapter to the outcome record.
- Payload remains open key-value; the table documents recommended keys, not a rigid schema.
- All 49 existing tests pass.
