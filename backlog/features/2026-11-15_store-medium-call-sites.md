---
id: "2026-11-15_store-medium-call-sites"
title: "Move Hidden Profile, Werewolf, and the session loop onto the store"
status: "Ready"
priority: "High"
created: "2026-11-15"
last_updated: "2026-11-15"
category: "features"
related_cips:
- "0016"
owner: "Christian Cabrera"
dependencies:
- "2026-11-15_addressed-observations"
- "2026-11-15_decision-shown-links"
tags:
- backlog
- hidden-profile
- werewolf
- documentation
---

# Task: Move Hidden Profile, Werewolf, and the session loop onto the store

## Description

Hidden Profile agents read their information from the store instead of receiving observations from the game loop.
Werewolf agents read through the visibility call instead of the unfiltered inspect call.
The session documentation shows the same shape.
The recommended loop no longer hands environment state around the store.

## Acceptance Criteria

- [ ] A Hidden Profile decision reads records from the store.
- [ ] The existing Hidden Profile question checks still pass once ids and clocks are set aside.
- [ ] Werewolf reads player-visible lines through the visibility call.
- [ ] A Werewolf agent cannot read a record the visibility rules hide.
- [ ] The session documentation recommends reading from the store.

## Implementation Notes

`experiments/information_flow/hidden_profile/run_doagent.py` passes observations into `decide`.
`experiments/multiagentbench/run_werewolf_doagent.py` reads `session.inspect("outcome")`.
The recommended loop is the docstring on `Session`.
Callers that still pass an explicit input keep working.

## Related

- CIP: 0016

## Progress Updates

### 2026-11-15

Task created from the accepted CIP-0016.
Not started.
Blocked by addressed observations and shown links.
