---
id: "2026-10-07_shadow-recording-baselines"
title: "Implement shadow recorders and fair representation baselines"
status: "Abandoned"
priority: "High"
created: "2026-10-07"
last_updated: "2026-10-15"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies:
- "2026-10-07_formal-information-channel-specification"
- "2026-10-07_controlled-information-flow-environment"
tags:
- backlog
- recording-policy
- baselines
- observability
---

# Task: Implement Shadow Recorders and Fair Representation Baselines

## Description

Implement recording policies that observe the same neutral event stream and retain different artifact representations.
The conditions are one local service log, partial service-log unions, the complete service-log union, competent structured service tracing, and DOAgent logging levels.
All conditions must observe the same execution without changing agent inputs or environment behaviour.

## Motivation

Separate service and DOAgent runs confound representation with stochastic trajectory differences.
Shadow recording removes that confound by capturing one execution under every policy.
Fair baselines are necessary because a comparison against only raw prose logs would overstate the architectural result.

## Justification

The experiment asks whether a recording policy preserves and exposes information.
The source event stream must therefore remain constant.
Differences in retained fields, links, duplication, indexing, and access are then properties of declared policies rather than differences in the underlying game.

## Recording Conditions

### S1

One named agent's local log retains only events visible to that service.

### Sk

A declared subset of local logs is available to the analyst.
Subset selection is generated independently of query outcomes.

### Sall

Every local service log is available.
This condition gives fragmented logging its strongest complete-data baseline.

### Sstructured

A central service trace stores competent telemetry fields.
The initial fields include timestamp, service identity, caller, callee, message identifier, payload, operation, status, and declared parent identifier where service tracing normally supplies one.
The schema must not copy DOAgent trace, provenance, or shared-data fields without independent justification.

### D0, D1, and D2

DOAgent sessions retain only the records and fields declared for each logging level.
Projection from a richer run is permitted only if it exactly matches what the lower level would have recorded.

## Execution Plan

1. Define one recorder protocol over neutral events.
2. Define field-availability matrices for every condition.
3. Implement local service-log writers with one artifact per agent.
4. Implement deterministic Sk subset selection.
5. Define Sall as the unchanged union of local artifacts.
6. Specify the structured service trace from neutral event and service-tracing semantics.
7. Implement the structured service-trace writer.
8. Implement a DOAgent shadow adapter from neutral events to session records.
9. Verify D0, D1, and D2 against current logging-level contracts.
10. Ensure every recorder consumes events after the environment has emitted them.
11. Prevent recorders from writing back into the environment or agent policy.
12. Measure recording bytes, records, duplicated payload, and wall time.
13. Test event parity across all attached recorders.
14. Test that prohibited fields are absent from each condition.
15. Document every intentional asymmetry as a recording-policy choice.

## Acceptance Criteria

- [ ] One execution feeds every recording condition.
- [ ] Recorders cannot alter environment state or agent observations.
- [ ] S1, Sk, Sall, Sstructured, D0, D1, and D2 have explicit field contracts.
- [ ] The structured service baseline is justified independently of DOAgent.
- [ ] Sall is the complete union of unchanged local logs.
- [ ] DOAgent levels match documented library semantics.
- [ ] Neutral event identifiers permit cross-condition parity tests.
- [ ] Every retained artifact can be traced to its source neutral event during validation.
- [ ] Private truth is unavailable to all recorders.
- [ ] Recording cost uses identical start and stop boundaries.
- [ ] Missing or duplicated events are reported rather than silently repaired.
- [ ] Recorder parity and field-exclusion tests pass.

## Implementation Notes

Do not make Sstructured deliberately weak.
Do not grant it DOAgent semantics merely to guarantee a tie.
Its purpose is to represent a competent service-oriented observability design.

Record source-event identifiers in validation metadata when required for parity testing.
Remove or hide validation-only identifiers from scored conditions if they would answer a query not supported by the declared policy.

## Dependencies and Gate

The neutral event contract and controlled environment must be stable.
This task provides the artifacts required by Gate 3.
Gate 3 cannot pass until a field-by-field fairness review confirms equal source events and honest policy differences.

## Related

- CIP: 0015
- Requirement: REQ-0015

## Progress Updates

### 2026-10-07

Task created to isolate representation policy from execution and to include a non-straw-man structured service baseline.

### 2026-10-15

Abandoned before implementation.
Shadow recorders would compare recorders written by the study rather than a real DOAgent session and a real service system.
The study now implements each environment twice, once on DOAgent and once on MARBLE, with shared rules and policies.
Scripted agents give identical trajectories, which keeps the fixed-history control this task was meant to provide.
The access conditions S1, Sk, Sall, Sstructured, D0, D1, and D2 carry over as views of the two implementations' artifacts.
See the Hidden Profile DOAgent and MARBLE implementation tasks.
