---
id: "2026-11-15_record-audience"
title: "Add an audience to records and apply it in the visibility filter"
status: "Completed"
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

- [x] A record can store an audience.
- [x] An empty audience does not hide the record from agents who already see that author.
- [x] A named audience hides the record from every other agent.
- [x] The rule holds for centralised, peer-to-peer, and federated topologies.
- [x] Existing records with no audience stay visible under the current rules.

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

### 2026-11-15

Completed.
The audience is a field on the record envelope, empty by default.
`new_record` accepts an audience.
`Session._records_visible_to` applies the topology rule first, then the audience.
The author of a record always reads it.
The federated hub must be named in an audience like any other agent.
An audience never shows a record to an agent that may not read its author.
`inspect` stays unfiltered.
Session files written before this change load with an empty audience.
Eight tests were added in `tests/test_session.py` and `tests/test_shared_data.py`.
The suite runs 375 tests.
Two fail, both before and after this change: the import in `test_hidden_profile_cost` and `test_proxy_key_is_read_from_dotenv`.

Peer-to-peer and federated topologies stay as they are.
An agent reads the environment only through an author it can already see, a peer or the hub.
An observation written by the environment stays hidden from an agent that cannot see that author.
