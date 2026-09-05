---
id: "2026-09-05_hub-membership-hook"
title: "Replaceable federated hub membership writes"
status: "Completed"
priority: "High"
created: "2026-09-05"
last_updated: "2026-09-05"
category: "features"
related_cips:
- "0003"
- "0004"
owner: "Christian Cabrera"
dependencies:
- "2026-09-05_visible-participants"
tags:
- backlog
- decentralisation
---

# Task: Replaceable federated hub membership writes

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

After join/leave in federated mode, the hub must write something leaves can see.
That write is now a hook (`topology.on_hub_membership`). Default is the current
roster snapshot. `relay_join_leave_as_hub` re-emits join/leave with `actor=hub`
and `member_id` set to the real agent.

## Acceptance Criteria

- [x] Default behaviour still writes a hub `roster` snapshot.
- [x] A custom hook can write nothing extra.
- [x] Built-in relay: leaves reconstruct membership from hub-authored join/leave.

## Related

- CIP: [0003](../../cip/cip0003_decentralisation-spectrum.md)
- Tests: `tests/test_session.py`, `tests/test_topology.py`

## Progress Updates

### 2026-09-05

Implemented. Tests passed. Marked complete.
