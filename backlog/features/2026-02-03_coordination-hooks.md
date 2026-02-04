---
id: "2026-02-03_coordination-hooks"
title: "Add coordination hooks for CIP-0003"
status: "Completed"
priority: "Medium"
created: "2026-02-03"
last_updated: "2026-02-03"
category: "features"
related_cips:
- "0003"
owner: "Christian Cabrera"
dependencies:
- "2026-02-03_topology-config"
tags:
- backlog
- decentralisation
---

# Task: Add coordination hooks for CIP-0003

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Expose a minimal coordination hook that responds to topology selection (no network transport yet).

## Acceptance Criteria
- [ ] Hook returns a routing decision based on topology.
- [ ] Hook is documented for later extension.

## Implementation Notes
Keep this as a stub that can be replaced by real coordination logic later.

## Related
- CIP: 0003
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-02-03
Task created.

### 2026-02-03
Set to In Progress. Implementing coordination hook stub.

### 2026-02-03
Added `select_routing` hook with a `RoutingDecision` result.

### 2026-02-03
Aligned federated description to “within federated controllers”.

### 2026-02-03
Marked complete after tests passed.
