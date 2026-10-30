---
id: "2026-10-07_common-query-decoding-pipeline"
title: "Implement the neutral evidence and common query pipeline"
status: "Ready"
priority: "High"
created: "2026-10-07"
last_updated: "2026-10-23"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies:
- "2026-10-07_formal-information-channel-specification"
- "2026-10-15_hidden-profile-environment"
- "2026-10-15_hidden-profile-doagent-implementation"
- "2026-10-15_hidden-profile-marble-implementation"
tags:
- backlog
- queries
- decoding
- observability
---

# Task: Implement the Neutral Evidence and Common Query Pipeline

## Description

Implement one representation-specific parser per artifact condition and one representation-independent query decoder.
Each parser maps retained artifacts into a neutral evidence model.
The common decoder answers the frozen query suite from that evidence without knowing which representation produced it.

## Motivation

A single parser cannot read incompatible raw formats.
Separate end-to-end decoders would allow representation-specific shortcuts and incomparable engineering effort.
The two-stage pipeline isolates unavoidable parsing differences while keeping query semantics and answer logic common.

## Justification

The parser is where representation accessibility is measured.
The common decoder is where question answerability is measured.
Separating them prevents the neutral evidence model from becoming a renamed DOAgent schema and prevents query logic from being tuned independently for each condition.

## Primary Query Set

The initial query suite includes:

- recipients of a named event
- agents with access to a named fact by a time point
- first event that made a fact accessible to an agent
- observation available to a named decision
- actor and selected action of a named decision
- recorded update supplied to a named transition
- declared inputs to a named decision
- global order of selected events

The suite excludes unconstrained questions about actual causal effect or responsibility.

## Execution Plan

1. Define the neutral evidence model from environment and query semantics.
2. Ensure the evidence model contains no DOAgent-only field names or assumptions.
3. Define parser outputs for exact evidence, missing evidence, conflicting evidence, and ambiguous evidence.
4. Implement the S1 parser.
5. Implement the Sk and Sall aggregation parser.
6. Implement the structured service-trace parser.
7. Implement D0, D1, and D2 parsers.
8. Instrument parsers to report files opened, bytes read, records scanned, joins, and runtime.
9. Define one common query decoder over neutral evidence.
10. Return exact answers, explicit unknown values, or finite candidate sets.
11. Prevent the decoder from consulting artifact paths, representation labels, or private truth.
12. Create pilot seeds for parser and decoder development.
13. Freeze parser rules and decoder logic before scored seeds are generated.
14. Hash or version the frozen implementations for reproducibility.
15. Test all conditions against the same truth-generated queries.
16. For each recovered path of a named fact, compute the mutual information between the correct option and each successive recorded copy of that fact.
17. Mark the reconstruction wrong when that mutual information increases from one hop to the next.

## Acceptance Criteria

- [ ] The neutral evidence model is justified from environment and query semantics.
- [ ] Every representation has a parser with the same output contract.
- [ ] One common decoder serves every representation.
- [ ] The decoder cannot identify the originating representation.
- [ ] Unknown and ambiguous answers are represented explicitly.
- [ ] Candidate sets obey protocol constraints fixed before artifact inspection.
- [ ] Parser cost counters use identical definitions.
- [ ] No parser reads private truth.
- [ ] No parser uses a field prohibited by its recording condition.
- [ ] Primary query fixtures cover exact, missing, ambiguous, and conflicting evidence.
- [ ] Pilot and scored seeds are separate.
- [ ] Parser and decoder versions are frozen before the scored campaign.
- [ ] Along a recovered path, mutual information between the correct option and successive copies of one named fact never increases.
- [ ] An increase is recorded as a reconstruction error.
- [ ] The check uses successive recorded copies of one named fact.
- [ ] An agent's pooled held set is scored as its own variable.

## Implementation Notes

Do not count manual researcher reasoning as a free decoder operation.
Protocol rules used by a parser or decoder must be declared and versioned.
If a service parser reconstructs an audience from several logs, report the join and bytes read.
If a DOAgent parser performs an indexed lookup, report the index requirement and lookup cost.

The common decoder may answer recorded dependency questions.
It must not translate a trace edge into a causal effect.

## Dependencies and Gate

The artifact contracts must be implemented before parser behaviour can be frozen.
This task must complete before estimator validation uses decoded answers.
Any post-freeze parser change invalidates scored results unless the complete campaign is rerun.

## Related

- CIP: 0015
- Requirement: REQ-0015

## Progress Updates

### 2026-10-07

Task created to make query logic independent of representation while treating parsing effort as an experimental outcome.

### 2026-10-15

Added a data-processing check on recovered fact paths.
Information about the correct option cannot increase from one recorded copy of a fact to the next.
A rise means the reconstruction added content the path did not carry.

### 2026-10-23

The eight primary questions and the three answer kinds are in `queries.py`.
An answer is one value, unknown, or a candidate set.
The decoder reads the rules' event list and does not read private truth.
Seed 0 is the check.
Agent C is dealt f6 and sends it to agent A in round 1.
The transition question is unknown, because Hidden Profile writes no transition event.
`parse.py` rebuilds those events from a session file and from the MARBLE logs.
The environment log names the dealt facts, and each agent log names the chosen action.
Seed 0 recovered from either file gives agent A as the recipient of f6, the same access after round 0 and round 1, and the hill votes.
The transition question stays unknown.
The parsers read those files and do not open the scoring record.
One agent log, the three agent logs, and every log are now separate views.
Every log still recovers the f6 path.
The three agent logs still show that agent A received f6, and access to f6 is unknown because the deal line is absent.
Agent C's log alone still names that recipient.
Agent B's log alone does not, so the recipient is unknown.
`compare.py` asks those questions of all 18 reference deals.
The full DOAgent session and every MARBLE log match the rules on each deal.
That covers who received the bridge fact, who could access it after round 0 and round 1, and the three hill votes.
The transition question stays unknown on every deal.
The three agent logs, with the deal line missing, leave bridge access unknown on every deal.
The recipient is still recovered from those logs.
`comparison.json` records the answers.
Each artifact view also records how many files were read, how many bytes those files contain, and how many cross-file joins built the event list.
A join is lining up two or more agent logs by round, or attaching the deal line from the environment log.
Matching fields inside one file is not a join.
On every deal the session file is one file and no joins.
One agent log is one file and no joins.
The three agent logs are three files and one join.
The environment log plus the three agent logs is four files and two joins.
The engine log is selected with every log and is not read, so its bytes are not counted.
Byte totals differ by deal because the files differ.
Records scanned and parser runtime are not counted yet.
This table is not a scored result.
An optional structured service trace now sits beside the prose logs.
Each line names the time, the service, the caller, the callee, the operation, a message id, the payload, a status, and the parent call.
The parent is the engine run.
The file does not carry session trace, provenance, or shared-data fields.
On every deal it matches the rules on the same questions as the full logs.
Reading it takes one file and no joins.
On these 18 deals the file is 4,411 bytes.
It is a stronger baseline than the prose logs, and the tie is not a scored result.
The query suite and the decoders are frozen for any later scored run.
The eight questions, the three answer kinds, `queries.py`, `parse.py`, and `service_trace.py` are the locked reading code.
The version-hash box stays open.
The Hidden Profile reference configuration is frozen in the CIP.
Nothing is scored.
The 18-deal tie is a cost result for message facts.
The questions in that table are written on the log line and do not need a trace.
The rules point each vote at a belief, and the belief at the observations behind it.
The session stores a trace at logging level 1.
The parsers do not read it, so both artifacts are scored with an empty input list.
