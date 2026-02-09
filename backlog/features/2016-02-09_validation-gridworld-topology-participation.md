---
id: "2016-02-09_validation-gridworld-topology-participation"
title: "Add topology modes and open participation to grid-world"
status: "Pending"
priority: "High"
created: "2016-02-09"
last_updated: "2016-02-09"
category: "features"
related_cips:
- "0010"
owner: "Christian Cabrera"
dependencies:
- "2016-02-09_validation-gridworld-env"
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
- [ ] Topology mode affects which shared-data updates agents receive.
- [ ] Agents can join/leave mid-run with registry updates.
- [ ] Scenario reflects resource changes when agents join/leave.

## Implementation Notes
Prefer opt-in flags for topology modes to keep current architecture intact and backward compatible.

## Related
- CIP: 0010
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2016-02-09
Task created.
