---
id: "2026-11-15_decision-shown-links"
title: "Take the default decision input from the store and record what was shown"
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
- "2026-11-15_addressed-observations"
- "2026-11-15_decision-message-split"
tags:
- backlog
- decisions
- provenance
---

# Task: Take the default decision input from the store and record what was shown

## Description

A decision with no explicit input reads the records that agent is allowed to see.
The library writes those record ids into the decision provenance.
The agent does not write this list.
A caller may still pass an explicit input, and that path keeps its current behaviour.
A run at logging level 0 still omits provenance.

## Acceptance Criteria

- [ ] A decision with no explicit input is built from visible records.
- [ ] The decision provenance lists the ids of the records that were shown.
- [ ] The library writes that list, not the policy.
- [ ] An explicit input still overrides the store.
- [ ] Logging level 0 writes no source list.
- [ ] An agent's own earlier records are part of what it can be shown.

## Implementation Notes

`RecordWriter.on_agent_decide` currently calls `new_provenance` with an empty source list.
`Session.decision_context` already applies the visibility rules.
Shown is not the same as used.
A policy may still attach its own claim about what it relied on.
That claim is not this list.

## Related

- CIP: 0016

## Progress Updates

### 2026-11-15

Task created from the accepted CIP-0016.
Not started.
Blocked by the audience, observation, and message tasks.
