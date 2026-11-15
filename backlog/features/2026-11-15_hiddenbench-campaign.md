---
id: "2026-11-15_hiddenbench-campaign"
title: "Run the HiddenBench pilot and campaign"
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
tags:
- backlog
- evaluation
- hiddenbench
---

# Task: Run the HiddenBench pilot and campaign

## Description

Run HiddenBench tasks with model-backed agents who read and write only through the store.
Each fact, utterance, and vote is a record.
Each run is recorded once and read three ways.
A pilot of three tasks decides whether the campaign continues.
The campaign varies discussion length, group size, visibility, and logging level.
Each wrong vote is classed as missing, not combined, or followed the group.

## Acceptance Criteria

- [ ] The licence of the HiddenBench materials is checked before the pilot.
- [ ] A few tasks run in the benchmark's own harness with the same model, as a behaviour check.
- [ ] The three-task pilot reports failure rate, withholding stability, and whether the judge already matches the query.
- [ ] The campaign reports accuracy, cost of answering, and cost of recording for each reading.
- [ ] Each wrong vote is placed in one failure class.
- [ ] A tie between the judge and the query is reported as a tie.
- [ ] Mention matching is scored on a hand-checked sample.

## Implementation Notes

The first configuration is four agents speaking in turn, with a vote before discussion and a vote after it.
Kimi is the first model.
A second open model is used when one is available.
A matching judge on the short pilot does not end the study.
A matching judge after the length and group-size factors does.
The call budget is fixed before the campaign.

## Related

- CIP: 0017

## Progress Updates

### 2026-11-15

Task created from the accepted CIP-0017.
Not started.
Blocked by the trace export and the decision repeat.
