---
id: "2026-11-15_decision-message-split"
title: "Separate private decision records from message records"
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
- decisions
- messages
---

# Task: Separate private decision records from message records

## Description

A decision record stays private to the acting agent.
It holds the inputs and the reasoning.
Anything other agents should see is a separate message record, addressed to those recipients.
An agent cannot learn another agent's reasoning by reading a record it is allowed to see.

## Acceptance Criteria

- [ ] A decision record is visible only to the acting agent.
- [ ] A message record is visible only to its audience.
- [ ] The message does not contain the acting agent's reasoning or full input.
- [ ] A later decision by the same agent can still read its own decision record.
- [ ] Peers can read the message without reading the decision.

## Implementation Notes

`SessionAgent.decide` currently writes one agent update that contains the request and the response.
The audience field comes from the record-audience task.
This task can proceed beside the addressed-observation task.

## Related

- CIP: 0016

## Progress Updates

### 2026-11-15

Task created from the accepted CIP-0016.
Not started.
Blocked by the audience filter.
