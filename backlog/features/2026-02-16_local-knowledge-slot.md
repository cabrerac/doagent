---
id: "2026-02-16_local-knowledge-slot"
title: "Add local_knowledge as required slot in agent_update payload"
status: "Completed"
priority: "High"
created: "2026-02-16"
last_updated: "2026-02-19"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies:
- "2026-02-16_data-model-spec"
tags:
- backlog
- shared-data
- agent-update
---

# Task: Add local_knowledge as required slot in agent_update payload

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Make `local_knowledge` a required slot in the agent_update payload. local_knowledge represents what the agent knows at update time (e.g. gridworld cells, push observations). Scenario-specific structure; the slot name and semantics are standardised. Always part of agent_update when agent_update exists.

## Acceptance Criteria

- [x] agent_update payload includes `local_knowledge` slot.
- [x] Gridworld map_update / map_summary record their content under `local_knowledge` (or equivalent).
- [x] Schema or types reflect local_knowledge as part of agent_update.
- [x] Documentation describes local_knowledge as scenario-defined content with temporal semantics (snapshot at update time).

## Implementation Notes

- In gridworld scenario: map_update cells, map_summary content → `local_knowledge` in payload.
- agent_update is produced for all agent steps (including push); for push, local_knowledge may be empty or contain observations.
- Structure inside local_knowledge is domain-specific; document the slot, not the schema.

## Related

- CIP: 0002
- PRs: N/A
- Documentation: Data model spec

## Progress Updates

### 2026-02-16
Task created.

### 2026-02-19
new_agent_update_record requires local_knowledge. Gridworld and push scenarios populate it. RecordWriter.on_agent_decide takes local_knowledge. Documented in data-model-spec.md §3. Marked complete.
