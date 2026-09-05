---
id: "2026-09-05_dynamic-topology"
title: "Join/leave updates the peer-to-peer visibility map"
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
- openness
---

# Task: Join/leave updates the peer-to-peer visibility map

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

YAML visibility is the graph for agents **named in it**. When someone **not** in that
file joins, they are linked both ways to everyone currently in. When anyone leaves,
they drop from every list. Listed agents keep (or restore) the YAML links.
Centralised and federated do not use this map.

Users may pass `topology.on_membership_change` for a different rule, or
`mesh_on_membership_change` for a full mesh including listed agents.

## Acceptance Criteria

- [x] Peer-to-peer join meshes only agents **not** named in the topology file.
- [x] Listed agents keep YAML links when they join.
- [x] Peer-to-peer leave removes them from the map; peers stop seeing their records.
- [x] A custom `on_membership_change` hook can keep the original YAML map.
- [x] Centralised and federated membership behaviour is unchanged.
- [x] Existing peer-to-peer tests that never register still use the static YAML map.

## Implementation Notes

Default hook: `make_default_membership_hook` (YAML for named agents; mesh strangers).
`mesh_on_membership_change` remains available for a full mesh.

## Related

- CIP: [0003](../../cip/cip0003_decentralisation-spectrum.md), [0004](../../cip/cip0004_open-participation.md)
- Tests: `tests/test_session.py`, `tests/test_topology.py`

## Progress Updates

### 2026-09-05

Implemented. Default: YAML for named agents, mesh only strangers. Tests passed.

### 2026-09-05 (later)

Default narrowed: mesh only agents not in the topology file.
