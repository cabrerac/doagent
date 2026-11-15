---
id: "2026-11-15_traitors-campaign"
title: "Build Traitors on the store and run its pilot and campaign"
status: "Ready"
priority: "High"
created: "2026-11-15"
last_updated: "2026-11-15"
category: "features"
related_cips:
- "0017"
owner: "Christian Cabrera"
dependencies:
- "2026-11-15_trace-export-and-judge"
- "2026-11-15_decision-repeat"
- "2026-11-15_record-audience"
tags:
- backlog
- evaluation
- traitors
---

# Task: Build Traitors on the store and run its pilot and campaign

## Description

Implement Traitors with the published rules and prompts, on our own environment.
Agents read and write only through the store.
Roles are records addressed to the agent who holds the role.
Traitor night talk is message records with a traitor-only audience.
Each run is recorded once and read three ways.
The new measure is the share of wrong faithful votes that change when traitor-written records are withheld.

## Acceptance Criteria

- [ ] The licence of the published prompts and rules is checked before the pilot.
- [ ] Faithful agents cannot read traitor night messages.
- [ ] A pilot at ten agents reports whether the withholding repeats are stable.
- [ ] The campaign reports the misled share beside the accountability, traceability, and explainability questions.
- [ ] Accuracy, cost of answering, and cost of recording are reported for each reading.
- [ ] The call budget is fixed before the campaign.
- [ ] Werewolf is not rerun as a scored scenario.

## Implementation Notes

The published setup is ten agents, three of them traitors, with night, discussion, and vote phases.
A published run uses about 500,000 tokens.
Their agents keep memory outside any store, so their code is not the system under test.
This task can be built after the judge exists.
It does not wait for the HiddenBench campaign to finish.

## Related

- CIP: 0017

## Progress Updates

### 2026-11-15

Task created from the accepted CIP-0017.
Not started.
Blocked by the trace export, the decision repeat, and the audience filter.
