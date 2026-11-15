---
id: "2026-11-15_addressed-observations"
title: "Write one addressed record per private observation"
status: "Ready"
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

- [ ] Reset writes one record per private item before any decision.
- [ ] Step writes one observation record per agent, addressed to that agent.
- [ ] An agent cannot read another agent's private observation record.
- [ ] The combined outcome remains available to existing readers.
- [ ] Tests cover a reset and a step with at least two agents.

## Implementation Notes

`WrappedEnv.reset` currently writes nothing.
`RecordWriter.on_outcome_and_traces` writes one outcome that contains every observation.
The audience field comes from the record-audience task.

## Related

- CIP: 0016

## Progress Updates

### 2026-11-15

Task created from the accepted CIP-0016.
Not started.
Blocked by the audience filter.
