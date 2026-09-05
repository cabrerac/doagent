---
id: "2026-09-05_visible-participants"
title: "Agents read who is in from topology-filtered participation records"
status: "Completed"
priority: "High"
created: "2026-09-05"
last_updated: "2026-09-05"
category: "features"
related_cips:
- "0004"
- "0003"
owner: "Christian Cabrera"
dependencies:
- "2026-09-05_participation-into-shared-data"
tags:
- backlog
- openness
- decentralisation
---

# Task: Agents read who is in from topology-filtered participation records

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Join/leave already land in the shared store. Agents still did not use those records to know who is available.
Membership at decision time must use the **same topology filter** as other records. Federated leaf agents only see
hub-authored records, so the hub republishes a `roster` event after each join or leave.

## Acceptance Criteria

- [x] `session.visible_participants(agent_id)` rebuilds current membership from visible `participation` records.
- [x] Centralised: an agent sees all current members.
- [x] Peer-to-peer: an agent sees only self and allowed peers.
- [x] Federated: the hub writes `event: "roster"`; leaf agents reconstruct membership from that.
- [x] Gridworld passes `participants` into `decide` inputs from `visible_participants`.

## Implementation Notes

Same filter as `visible_records`. Do not give agents a global roster. Replay join/leave in write order; a roster
event replaces the view. Keep the in-memory registry as the per-run index and as the source of the hub roster.

## Related

- CIP: [0004](../../cip/cip0004_open-participation.md), [0003](../../cip/cip0003_decentralisation-spectrum.md)
- Documentation: `docs/data-model-spec.md` §3.3
- Tests: `tests/test_session.py` (`test_visible_participants_*`)

## Progress Updates

### 2026-09-05

Implemented and tests passed. Marked complete.
