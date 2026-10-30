---
id: "2026-10-07_controlled-observability-campaign"
title: "Run the controlled observability campaign"
status: "Completed"
priority: "High"
created: "2026-10-07"
last_updated: "2026-10-30"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies:
- "2026-10-15_hidden-profile-doagent-implementation"
- "2026-10-15_hidden-profile-marble-implementation"
- "2026-10-07_common-query-decoding-pipeline"
- "2026-10-07_information-estimator-validation"
tags:
- backlog
- experiment
- observability
- information-cost
---

# Task: Run the Controlled Observability Campaign

## Description

Run the frozen controlled experiment across all recording conditions.
Measure retained information, residual ambiguity, query accuracy, analysis cost, and recording cost.
Construct the information-cost frontier and apply Gates 3 and 4.

## Motivation

The preceding tasks build and validate the measuring apparatus.
This task produces the first scored evidence about whether DOAgent facilitates information-flow analysis relative to complete and partial service logs and structured service tracing.

## Justification

The campaign must preserve null results, ties, and service advantages.
Its purpose is not to produce a predetermined ranking.
Its purpose is to reveal which recording policies are sufficient for which questions and what each sufficiency level costs.

## Pre-Run Checklist

The campaign cannot start until:

- Gate 1 has passed
- Gate 2 has passed
- the environment configuration is frozen
- scored seeds are reserved
- recorder field contracts are frozen
- parser and decoder versions are frozen
- cost boundaries are frozen
- primary hypotheses and metrics are registered
- structured baseline fairness is reviewed

## Execution Plan

1. Create an immutable campaign manifest.
2. Record code revision, configuration versions, estimator versions, and seeds.
3. Run an unscored end-to-end dry run.
4. Confirm that every recorder consumed the same neutral events.
5. Confirm that private truth is absent from scored artifacts.
6. Run the sample count selected by estimator validation.
7. Preserve every successful, failed, and discarded episode with a reason.
8. Parse artifacts into neutral evidence using frozen parsers.
9. Answer the frozen query suite with the common decoder.
10. Compare decoded answers against private truth.
11. Compute exact answerability and residual ambiguity.
12. Compute validated Shannon quantities and calibration scores.
13. Aggregate analysis cost by condition and query family.
14. Aggregate recording bytes, duplication, records, and wall time.
15. Bootstrap uncertainty across independent episodes.
16. Construct per-query and aggregate information-cost frontiers.
17. Perform the Gate 3 fairness audit.
18. Perform the Gate 4 measurable-result review.
19. Record ties, disadvantages, and failed hypotheses.
20. Decide which gated extensions have empirical justification.

## Acceptance Criteria

- [x] Campaign inputs and scored seeds are immutable and recorded.
- [x] Every condition receives identical neutral source events.
- [x] Every episode has separate private truth and analysed artifacts.
- [x] All declared primary metrics are reported.
- [x] Missing, failed, and discarded episodes are accounted for.
- [x] This game lists every deal, so the score has no sample interval.
- [x] Information retention and analysis cost are reported separately.
- [x] Recording cost uses identical boundaries.
- [x] S1, Sk, Sall, Sstructured, D0, D1, and D2 are included.
- [x] Results report DOAgent wins, ties, and losses without filtering.
- [x] The information-cost frontier is produced.
- [x] Gates 3 and 4 receive explicit pass or fail decisions.
- [x] Extension tasks remain blocked unless their prerequisites pass.

## Implementation Notes

Do not change parsers, decoders, estimators, or hypotheses after inspecting scored results.
If a defect requires a change, invalidate the affected campaign and rerun all conditions.

Aggregate results only after preserving per-query and per-policy values.
A single scalar ranking is optional and must not hide trade-offs.

## Dependencies and Gate

This task is the final core implementation task for CIP-0015.
Its successful completion through Gate 4 unlocks consideration of the extension tasks.
It does not automatically authorize LLM, Werewolf, causal, transfer-entropy, or information-topography experiments.

## Related

- CIP: 0015
- Requirement: REQ-0015

## Progress Updates

### 2026-10-07

Task created as the scored core campaign and decision point for all later extensions.

### 2026-10-29

All 18 deals were scored.
None failed and none were discarded.
The rules are the true answers.
The session file and the MARBLE files are read separately.
Session levels 0, 1, and 2 are included.
So are one log, the three agent logs, all component logs, and the structured file.
Level 1 and level 2 match every asked question.
They average 77,012 bytes.
Level 0 matches 198 of 324 answers and averages 66,102 bytes.
Agent C's log matches 48 answers and averages 460 bytes.
The three agent logs match 108 answers and average 1,380 bytes.
All component logs match 162 answers.
They average 1,831 bytes read and 1,995 bytes stored.
The structured file matches 162 answers and averages 4,411 bytes.
Stored bytes are the files that view keeps.
Bytes read are the files the analyst opens.
The same rule is used for every view.
Level 1 against all component logs has 162 wins, 162 ties, and no losses.
The plot is written beside the score file.
Checkpoint 4 passes.
This game has no sample interval, so that line stays open.
The other declared measures stay open.
The extension games are not started.
Belief entropy, holder entropy, delivery information, and multi-information are now plotted.
The session file matches the rules on all four.
The MARBLE files do not state belief entropy.
All component logs and the structured file match the other three.
Agent C's log and the three agent logs do not.
Other declared measures stay open.

### 2026-10-30

The question grid and the dimension summary are written beside the score.
Record questions and link questions are counted separately.
Accountability, traceability, and explainability each have their own bars.
Session levels 1 and 2 recover the stated questions in all three.
The logs recover many record questions and miss the links and the chances.
The bit charts repeat the rules when a file states the inputs.
The figures sit in output/hidden_profile, with no timestamp.
Git ignores that folder.
One timestamped study command is the next task.
It has not been started.
The open lines above stay open.
The scored run is output/hidden_profile_20261030_011812.
campaign.json records the 18 deals, logging levels 0, 1, and 2, and commit 386d1a8.
The study command, the recovery curves, and the campaign code are still untracked.
Relative entropy of the reported chances is 0 for the rules and for every session level.
The Brier score is 0.153 and log loss is 0.493 bits.
MARBLE views do not state those chances.
Vote uncertainty given the named belief is 0 for the rules and for levels 1 and 2.
Level 0 and every MARBLE view leave that number unstated.
There is no sample interval, because every deal is in the score.
A later game that cannot list every deal still needs one.
The group guessing game, LLM agents, and Werewolf are not started.
