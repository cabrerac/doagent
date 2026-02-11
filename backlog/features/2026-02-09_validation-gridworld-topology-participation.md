---
id: "2026-02-09_validation-gridworld-topology-participation"
title: "Add topology modes and open participation to grid-world"
status: "Completed"
priority: "High"
created: "2026-02-09"
last_updated: "2026-02-09"
category: "features"
related_cips:
- "0010"
owner: "Christian Cabrera"
dependencies:
- "2026-02-09_validation-gridworld-env"
tags:
- backlog
- validation
- decentralisation
- participation
- iteration-2
---
# Task: Add topology modes and open participation to grid-world

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Implement topology-driven visibility (centralised/federated/peer-to-peer) and support join/leave events using the participation registry during a run.

## Acceptance Criteria
- [x] Topology mode affects which shared-data updates agents receive.
- [x] Agents can join/leave mid-run with registry updates.
- [x] Scenario reflects resource changes when agents join/leave.

## Implementation Notes
Prefer opt-in flags for topology modes to keep current architecture intact and backward compatible.

## Related
- CIP: 0010
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-02-09
Completed topology-driven visibility and stochastic join/leave via energy model.
