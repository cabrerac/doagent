---
id: "2026-11-15_record-audience"
title: "Add an audience to records and apply it in the visibility filter"
status: "Ready"
priority: "High"
created: "2026-11-15"
last_updated: "2026-11-15"
category: "features"
related_cips:
- "0016"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- shared-data
- visibility
---

# Task: Add an audience to records and apply it in the visibility filter

## Description

A record may name the agents who are allowed to read it.
The visibility filter keeps a record only when the reader may see the author and is in that audience.
An empty audience means every agent who may see the author.
The three existing topologies stay as they are.
Audience is an extra filter, not a new topology.

## Acceptance Criteria

- [ ] A record can store an audience.
- [ ] An empty audience does not hide the record from agents who already see that author.
- [ ] A named audience hides the record from every other agent.
- [ ] The rule holds for centralised, peer-to-peer, and federated topologies.
- [ ] Existing records with no audience stay visible under the current rules.

## Implementation Notes

The filter lives in `Session._records_visible_to`.
The envelope is `SimpleRecord`.
Do not add a fourth topology.

## Related

- CIP: 0016

## Progress Updates

### 2026-11-15

Task created from the accepted CIP-0016.
Not started.
