---
id: "2026-11-15_addressed-observations"
title: "Write one addressed record per private observation"
status: "Completed"
priority: "High"
created: "2026-11-15"
last_updated: "2026-11-15"
category: "features"
related_cips:
- "0016"
owner: "Christian Cabrera"
dependencies:
- "2026-11-15_record-audience"
tags:
- backlog
- shared-data
- observations
---

# Task: Write one addressed record per private observation

## Description

Reset and step write each agent's private information as its own record, addressed to that agent.
Starting information is in the store before the first decision.
A combined outcome that holds every agent's observation may stay for current readers until those readers move.

## Acceptance Criteria

- [x] Reset writes one record per private item before any decision.
- [x] Step writes one observation record per agent, addressed to that agent.
- [x] An agent cannot read another agent's private observation record.
- [x] The combined outcome remains available to existing readers.
- [x] Tests cover a reset and a step with at least two agents.

## Implementation Notes

`WrappedEnv.reset` currently writes nothing.
`RecordWriter.on_outcome_and_traces` writes one outcome that contains every observation.
The audience field is available.
The audience filter is complete.
In peer-to-peer and federated topologies an agent reads the environment only through an author it can already see, a peer or the hub.
An observation written by the environment stays hidden from an agent that cannot see that author.

## Related

- CIP: 0016

## Progress Updates

### 2026-11-15

Task created from the accepted CIP-0016.
Not started.
The audience filter it depends on is complete.

### 2026-11-15

Completed.
`RecordWriter.on_addressed_observations` writes one record of kind "observation" per agent.
`WrappedEnv.reset` calls it with round 0.
`WrappedEnv.step` calls it with the step round, then still writes the combined outcome.
The environment is the author and the audience is that one agent.
A reset that does not return a dict writes no observation records.
In a peer-to-peer setup the records stay hidden unless the environment is already a visible author.
Four tests were added in `tests/test_session.py`.
