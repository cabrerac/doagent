---
id: "2026-11-15_decision-repeat"
title: "Repeat one decision with records withheld or added"
status: "Ready"
priority: "High"
created: "2026-11-15"
last_updated: "2026-11-15"
category: "features"
related_cips:
- "0016"
owner: "Christian Cabrera"
dependencies:
- "2026-11-15_decision-shown-links"
tags:
- backlog
- decisions
- replay
---

# Task: Repeat one decision with records withheld or added

## Description

One recorded decision can be run again with a named set of records withheld or added.
Every other input stays as it was.
The call can be repeated a stated number of times.
Each repeat is stored and linked to the original decision.
The repeat does not continue the rest of the run.

## Acceptance Criteria

- [ ] A repeat uses the original shown records except for the named withheld or added set.
- [ ] Other agents' later actions are not re-simulated.
- [ ] A stated repeat count runs the original input and the changed input the same number of times.
- [ ] Each repeat is stored as a record linked to the original decision.
- [ ] A scripted policy with a known effect of removing one record is covered by a test.

## Implementation Notes

The first version may live beside the session if the call shape is still moving.
The stored link and the fixed rest of the input belong to this task either way.
This is not the environment-level causal intervention task from 2026-10-07.
That task replays an environment transition.
This task replays one decision.

## Related

- CIP: 0016

## Progress Updates

### 2026-11-15

Task created from the accepted CIP-0016.
Not started.
Blocked by the shown-link task.
