---
id: "2026-02-16_remove-payload-redundancy"
title: "Remove provenance/accountability from payloads (record level only)"
status: "Completed"
priority: "High"
created: "2026-02-16"
last_updated: "2026-02-19"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- shared-data
- provenance
- accountability
---

# Task: Remove provenance/accountability from payloads (record level only)

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Eliminate redundancy by keeping provenance and accountability only at the record envelope level. Remove duplicate `accountability` and `provenance` from `agent_update.payload.decision.response` (or equivalent), and any other payload-level duplication. The envelope is the single source of truth.

## Acceptance Criteria

- [ ] Provenance and accountability are not duplicated inside agent_update payload (e.g. in decision.response).
- [ ] Record envelope is the single source of truth for provenance and accountability.
- [ ] Validation output (push, gridworld) shows no redundant provenance/accountability in payloads.
- [ ] Documentation updated to state the rule: provenance/accountability at envelope only.

## Implementation Notes

- In `doagent.core.function_agent` or agent_update/decision creation: stop copying provenance/accountability into payload.
- Decision is inside agent_update; ensure no duplication in that path.
- Keep envelope fields populated where applicable.

## Related

- CIP: 0002
- PRs: N/A
- Documentation: Data model spec

## Progress Updates

### 2026-02-16
Task created.

### 2026-02-19
Scenarios strip provenance/accountability from decision.response before writing. RecordWriter applies them at envelope level only. Documented in data-model-spec.md §5. Marked complete.
