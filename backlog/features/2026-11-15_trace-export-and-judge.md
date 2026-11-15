---
id: "2026-11-15_trace-export-and-judge"
title: "Add the model caller, the trace export, and the judge"
status: "Ready"
priority: "High"
created: "2026-11-15"
last_updated: "2026-11-15"
category: "features"
related_cips:
- "0017"
owner: "Christian Cabrera"
dependencies:
- "2026-11-15_hidden-profile-store-calibration"
tags:
- backlog
- evaluation
- traces
- judge
---

# Task: Add the model caller, the trace export, and the judge

## Description

Add a caller for a model-backed policy, starting with Kimi on the university machines.
Write each call's prompt and output as a trace export.
The export contains no record ids.
Add a judge that answers the same questions from traces and from session records.
Test the judge on the scripted Hidden Profile run, where the true answers are known, before using it on model-backed runs.

## Acceptance Criteria

- [ ] One model call writes a prompt and an output with no record ids in the export.
- [ ] The same questions can be sent to the judge for a trace reading and a record reading.
- [ ] On the scripted calibration run, the judge's errors against the exact answers are reported.
- [ ] Kimi limits that block a run are recorded.
- [ ] The caller does not require a second, separate execution of the game.

## Implementation Notes

The trace is captured where the model is called.
It must not include record ids, or the trace reading could use the store's links.
The judge is one model for both readings.
CIP-0011 is the existing model-agent work.

## Related

- CIP: 0017
- CIP: 0011

## Progress Updates

### 2026-11-15

Task created from the accepted CIP-0017.
Not started.
Blocked by the scripted calibration.
