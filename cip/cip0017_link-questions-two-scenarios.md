---
author: "Christian Cabrera"
created: "2026-11-15"
id: "0017"
last_updated: "2026-11-16"
status: "In Progress"
compressed: false
related_requirements:
- "0017"
- "0016"
- "0015"
- "0006"
- "0007"
- "0009"
related_cips:
- "0016"
- "0015"
- "0014"
- "0011"
tags:
- cip
- evaluation
- interpretability
- hidden-profile
- traitors
- link-questions
title: "Link Questions on HiddenBench and Traitors"
---

# CIP-0017: Link Questions on HiddenBench and Traitors

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [x] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented
- [ ] Deferred - Postponed

## Summary

This CIP evaluates whether link questions about group behaviour are answered by lookup on a DOAgent session, while the same questions have to be inferred from full per-agent prompt traces.
The events of a run are recorded once.
Three readings of those events are compared.
The first study is information pooling on HiddenBench.
The second is deception on Traitors.
A scripted Hidden Profile run checks the links before either model-backed campaign.

The claim is conditional on CIP-0016.
The store has to be the only medium, and the library has to record which records each decision was shown.
This CIP does not itself change that contract.

**Which requirements does this CIP address?** REQ-0017, with REQ-0016 as a precondition and REQ-0015 as the earlier observability study.

## Motivation

CIP-0015 showed that a scripted Hidden Profile session answers link questions that component logs miss.
The logs in that study store one line per action.
A full prompt trace records each call's inputs, and published failure-attribution work finds that those inputs are what make step-level questions answerable at all.
Against that stronger baseline, the scripted result no longer shows a difference in content.
It shows a difference between a stated link and a link a model must work out.

The questions that stay hard are the ones no single agent's trace contains.
Who held a fact.
Who was shown it before deciding.
Whether the decision used it.
Which chain of records produced the group result.

Published benchmarks already score the outcomes of these situations.
HiddenBench reports that groups with distributed facts reach about 30 percent accuracy, against about 81 percent for one agent given every fact.
Its diagnosis uses group-level interventions and a few quoted messages.
A second Hidden Profile study reports models that share most of their private facts and still fail to combine them.
The two accounts disagree, and neither answers the question vote by vote.
The Traitors framework studies deception with ten agents, a private channel, and outcome metrics such as survival and vote switching.
Its authors say they cannot tell strategic misdirection apart from a faithful agent's own reasoning failure.
TraceElephant reports that a judge with full traces names the responsible agent about 66 percent of the time and the responsible step about 30 percent of the time, on runs of roughly 20 to 30 model calls.

The open measurement is the cross-agent chain, answered by lookup, on runs long enough that reading every prompt is hard.

## Detailed Description

### Claim

When agents exchange information only through the store, link questions about group behaviour are answered by lookup.
With full per-agent prompt traces, the same questions are inferred by a model.
The gap is expected to grow with discussion length and group size.
That growth is a hypothesis.

If the judge on full traces matches the query at every length, the claim shrinks to cost, and the paper says so.

### One run, three readings

Each run is recorded once.
A neutral event log written by the game engine holds the true answers.
It is not shown to the judge or to the query.

| Reading | Evidence | Answered by |
|---|---|---|
| Traces | Each agent's full prompt and model output | A judge model |
| Records, judged | Session records | The same judge |
| Records, queried | Session records | Query code |

The middle reading separates the effect of the evidence from the effect of the answering method.
A separate service system is not used for these two scenarios.
CIP-0015 already compares a session with MARBLE on the scripted game.
Here the events must be identical, so only the evidence differs.

The trace export is written where the model is called.
It contains the prompt and the output.
It contains no record ids.

### Withholding test

The withholding test repeats one decision with the same input except for a named set of records, then compares the decision with the original.
It is the check on whether a decision used those records.

Three rules keep the test honest.

Models vary between calls, so each test repeats the original input and the changed input the same number of times, and the vote counts are compared.
When several records state the same fact, they are withheld together.
The test covers one decision.
It does not re-simulate everything that followed.

The same test can be done on a prompt trace by editing text.
It is the ground truth for "used" in both readings.
It is not, by itself, a DOAgent advantage.
The advantage claimed for the store is that the set to withhold is a list of record ids, already linked, rather than a passage to find inside several prompts.

### What the difference can and cannot be

A full prompt trace holds the same text the agent saw.
The session does not win by containing more text.
It can win because the links are stored when the decision is made, because the chain is in one store, and because the inputs of a decision are a defined set of records that can be withheld.

A question about a single voter is often already answered by that voter's own prompt.
The expected gap is on questions that join several agents.

### Scenario 1, HiddenBench

Tasks come from the public benchmark.
The first configuration is four agents speaking in turn over several rounds, with a vote before discussion and a vote after it.
Agents are backed by Kimi, and by a second open model when one is available on the university machines.
Each fact is one record.
Each utterance is a message record.
Each vote is a decision record.
Agents read other agents only through the store.

| Dimension | Record questions | Link questions |
|---|---|---|
| Accountability | Who held each fact? Who voted what? | Which votes produced the group result? Who held a fact that was never stated and still had turns left to speak? |
| Traceability | Was the fact stated, by whom, and when? | Who had been shown it before voting? By what path? Which facts was each voter missing? |
| Explainability | What reason did each voter give? | Does the vote change when the fact is withheld or added? Does the stated reason match the test? |

Each wrong vote is placed in one class.

Missing means a needed fact was never shown, either because it was never stated or because it was stated too late.
Adding it should change the vote.
Not combined means every needed fact was shown and the vote is still wrong.
Followed the group means the vote changes when the other agents' stated preferences are withheld.

The spread of these classes is the finding that speaks to the disagreement between the published studies.
One study places the failure on facts that were never surfaced.
The other places it on facts that were shared and not combined.

The factors are discussion length, group size, limited visibility between agents, and logging level.
Level 0 is included because it has no stored links, and the query reading should fail there in the same way CIP-0015 already measured.

### Scenario 2, Traitors

The game follows the published framework.
Ten agents, three of them traitors.
Each round has a night phase, a discussion, and a vote.
The implementation is our own environment, using that framework's rules and prompts.
Their agents keep memory outside any store, so their code is not the system under test.
Roles are records addressed to the agent who holds the role.
Traitor night talk is message records with a traitor-only audience.
Faithful agents cannot read those records.
This is the audience filter from CIP-0016.

| Dimension | Record questions | Link questions |
|---|---|---|
| Accountability | Who wrote each message and each vote? | Which votes banished a player? Whose messages had those voters been shown? |
| Traceability | Who could read each message? | Who knew a player's role, and from which round? What had each voter been shown before voting? |
| Explainability | What reason did each voter give? | Does the vote change when traitor-written records are withheld? Does it change when earlier votes are withheld? |

The new measure is the share of wrong faithful votes that change when every traitor-written record is withheld.
A change means the voter was misled.
No change means the error was the voter's own.
The framework's authors name this split as something their metrics cannot make.
In the store, "all records written by traitors" is one query.
In the traces, it is an edit inside each faithful agent's prompt.

Werewolf is the same family of game and already runs in this repository.
It stays background.
Traitors is the scenario that is recognisable, and it adds a private channel and a final vote that Werewolf does not provide.
Reusing Werewolf was the alternative, and it was set aside on those grounds.

### Measures

Accuracy is reported per reading, per dimension, and per record or link question.
Cost of answering is judge tokens and judge time, against query time.
Cost of recording is bytes stored and added run time, per logging level.
Stated against tested is how often the reason the agent gave matches the withholding test.
Scenario findings are the failure classes for HiddenBench and the misled share for Traitors.

### Mention matching

A free-text message does not carry the id of the fact it states.
Deciding that a message states a given fact needs a text comparison in both readings.
The comparison is a small check of its own.
A hand-checked sample scores it, and the score is reported with the query results.
Prompts do not carry record ids.
Agents give reasons in free text.
A later variant may let agents cite record labels.
That variant is not part of the first campaigns, because it would hand the query reading a link the agent was told to write.

### Calibration and pilots

The scripted Hidden Profile game is rerun through the store after CIP-0016.
Its questions already have exact answers.
This checks that the new links are right before any model is involved.
The existing information-theoretic scores stay with CIP-0015 and are not recomputed here.

A pilot then runs three HiddenBench tasks with Kimi.
The pilot continues into the campaign only if three things hold.
The groups fail often enough to classify.
The withholding repeats are stable enough to call a change.
The judge on the traces does not already match the query on these short tasks.
A matching judge on the short pilot does not end the study.
The hypothesis says the gap opens as runs get longer.
It does end the study if the judge still matches after the length and group-size factors.

Traitors gets its own pilot after the HiddenBench pilot, at the published size of ten agents.
A published run of that game uses about 500,000 tokens.
The call budget is fixed before the campaign.

### Factors and the negative result

Discussion length, group size, visibility, and how many agents' traces the auditor is allowed to read are the factors.
The last one matters because a trace reading gets weaker as more of the run is missing, while the store still answers from the records the auditor is allowed to read.
That comparison is only valid under the audience rules, since both readings must hide the same records.

A tie on accuracy is reported as a tie.
The cost figures are still reported.
No chart is dropped because it fails to favour the session.

### Checks still open

Kimi rate limits and context limits are not yet measured.
The licences of the HiddenBench materials and the Traitors code are not yet checked.
The classic shared-data literature, including tuple spaces and blackboard systems, has not been searched.
Whether Kimi groups fail often enough is what the pilot is for.
The HiddenBench appendix was not read when this plan was written.
If that appendix already traces each fact and each vote, the scenario stays and the claim text changes.

### What this study does not do

It does not rerun the attribution campaign.
It does not rerun Werewolf as a scored scenario.
It does not run the group guessing game.
Published work already measures information quantities on that game.
It does not claim that the session contains text the traces lack.
It does not treat an agent's stated reason as evidence that the named record was used.

## Implementation Plan

1. Accept CIP-0016 and land the library contract, including the decision repeat.
2. Rerun scripted Hidden Profile through the store and compare with the existing exact answers.
3. Add the model caller, the trace export, and the judge, with no record ids in the traces.
4. Run the three-task HiddenBench pilot and apply the pilot gate.
5. Run the HiddenBench campaign across the factors.
6. Implement the Traitors environment on the store, using the published rules and prompts.
7. Run the Traitors pilot, then the campaign.
8. Write the results into the paper only after both campaigns, or after a gate stops one of them.

## Backward Compatibility

This CIP adds experiment code and does not change the public library.
Library changes belong to CIP-0016.
Existing CIP-0015 outputs stay the record of the scripted information-theoretic study.

## Testing Strategy

The calibration run must reproduce the scripted question answers once ids and clocks are set aside.
The judge is tested on the calibration run, where the true answers are known, before it is trusted on model-backed runs.
The withholding test is checked on the scripted policies, where withholding a fact has a known effect.
Mention matching is scored on a hand-checked sample and the score is stored with the campaign.
A small number of HiddenBench tasks are also run in that benchmark's own harness, with the same model, as a behaviour check that our environment has not changed the game.

## Related Requirements

- REQ-0017, link questions about group behaviour on one run read three ways.
- REQ-0016, the store is the only medium.
- REQ-0015, the information-theoretic study this evaluation follows.
- REQ-0006, explanations of decisions.
- REQ-0007, traceable decision chains.
- REQ-0009, accountability for outcomes.

## Backlog Tasks

- [Calibrate the new links on scripted Hidden Profile](../backlog/features/2026-11-15_hidden-profile-store-calibration.md)
- [Add the model caller, the trace export, and the judge](../backlog/features/2026-11-15_trace-export-and-judge.md)
- [Run the HiddenBench pilot and campaign](../backlog/features/2026-11-15_hiddenbench-campaign.md)
- [Build Traitors on the store and run its pilot and campaign](../backlog/features/2026-11-15_traitors-campaign.md)

The library tasks that these depend on are listed in CIP-0016.

## Implementation Status

- [x] CIP-0016 contract available
- [x] Scripted Hidden Profile rerun through the store
- [x] Model caller, trace export, and judge
- [ ] HiddenBench pilot and gate
- [ ] HiddenBench campaign
- [ ] Traitors environment
- [ ] Traitors pilot and campaign
- [ ] Results written into the paper

## References

- CIP-0016, the library contract this study requires.
- CIP-0015, the scripted Hidden Profile study and its link-question result.
- CIP-0014, the Werewolf information-flow study, kept as background.
- CIP-0011, model-backed agents.
- HiddenBench, arXiv 2505.11556.
- Hidden Profile decision making in multi-agent LLM groups, CSCW 2026 companion, doi 10.1145/3785651.3831525.
- The Traitors, arXiv 2505.12923.
- TraceElephant, arXiv 2604.22708.
- Auditable Agents, arXiv 2604.05485.
- TriEx, arXiv 2604.20043.
- `experiments/information_flow/hidden_profile/`, the calibration game.
- `backlog/features/2026-10-07_causal-intervention-extension.md`, an earlier proposal for replay, scoped to environment transitions rather than to one decision.

## Progress Updates

### 2026-11-15

CIP drafted.
The baseline is one run read three ways.
HiddenBench is the first scenario and Traitors is the second.
Status is Proposed.
No experiment code is authorised by this document alone.

### 2026-11-15

Status moved to Accepted.
Backlog tasks are not created yet.
CIP-0016 remains the precondition for the library contract.

### 2026-11-15

Four backlog tasks were added.
All four wait on the CIP-0016 tasks.
No task is in progress.

### 2026-11-16

The scripted Hidden Profile game reads the store.
All 18 deals were rerun at logging levels 0, 1, and 2.
Level 1 and level 2 store the shown-record links.
Level 0 stores none.
Withholding the observation record stops the scripted disclosure.
The information-theoretic scores were not recomputed.

### 2026-11-16

A model call writes its prompt and its output while the call happens.
The export refuses record ids.
A rate limit or a context limit is stored on that same call, and the call still stops.
The judge is asked the same questions about the trace text and about the session records.
On the scripted Hidden Profile run, a judge that matches the exact answers has no errors, and a judge that does not is reported.
