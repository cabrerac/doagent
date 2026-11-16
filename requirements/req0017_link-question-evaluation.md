---
id: "0017"
title: "Link Questions about Group Behaviour"
status: "In Progress"
priority: "High"
created: "2026-11-15"
last_updated: "2026-11-16"
related_tenets:
- "interpretability-and-traceability"
- "provenance-and-accountability"
- "data-first-shared-model"
- "model-agnostic-core"
stakeholders:
- "multi-agent system researchers"
- "auditors"
- "system operators"
tags:
- requirements
- evaluation
- interpretability
- accountability
- traceability
- explainability
---

# REQ-0017: Link Questions about Group Behaviour

## Description

An analyst must be able to answer record questions and link questions about one multi-agent run.
A record question is answered from the contents of one record.
A link question needs a stated connection between records, such as who was shown a fact before voting, or which votes produced the group result.

The same events must be readable in three ways.
One way is the full prompt trace of each agent, answered by a judge model.
One way is the session records, answered by the same judge.
One way is the session records, answered by query.
The events stay identical.
Only the evidence and the answering method change.

The questions cover three dimensions.
Accountability asks who held information and who produced an outcome.
Traceability asks what was stated, who was shown it, and by what path.
Explainability asks what reason was given and whether a repeated decision supports that reason.

The comparison must cover two settings.
One setting is information pooling where a correct group decision is known.
The other is deception under hidden roles, with a private channel between a subset of agents.
Both settings use model-backed agents.

Results must report answer accuracy, the cost of answering, and the cost of recording.
Where a stated reason can be checked by repeating the decision, the check is reported beside the stated reason.
A tie is a valid result and must be reported as a tie.

REQ-0015 measures how much information a recording keeps, using information-theoretic quantities on a scripted game.
This requirement asks whether link questions about group behaviour are answered by lookup once agents are backed by models.
REQ-0016 is a precondition, because the links are meaningful only when the store is the only medium.

**Why this matters**: Questions about behaviour that no single agent shows are chains across agents.
The interpretability tenet requires those chains to be explainable.
The provenance tenet requires them to be traceable to the records that were actually shown.

**Who benefits**: Multi-agent system researchers, auditors, and system operators.

## Acceptance Criteria

- [ ] One run can be read as per-agent full prompt traces and as session records, and both readings describe the same events.
- [ ] Record questions and link questions are stated for accountability, traceability, and explainability.
- [ ] The same questions are answered by a judge on the traces, by that judge on the records, and by query on the records.
- [ ] Accuracy, cost of answering, and cost of recording are reported separately for each reading.
- [x] A repeated decision with named records withheld or added is available as a check on stated reasons.
- [ ] The information-pooling setting has a known correct decision and classifies each wrong vote.
- [ ] The deception setting has hidden roles, a private channel, and a reported share of wrong votes that change when records from the deceiving agents are withheld.
- [x] A scripted run with exact answers checks the links before any model-backed campaign.
- [ ] Ties and cases where the query does not beat the judge are reported as such.

## Notes

The information-pooling setting is HiddenBench.
The deception setting follows the published Traitors framework, implemented so that agents read and write the store.
The scripted Hidden Profile study remains the calibration case.
Attribution and Werewolf stay background.
The group guessing game is not part of this requirement.

A full prompt trace already shows one agent what that agent was given.
The expected difference is on questions that cross agents, and it is expected to grow with discussion length and group size.
That growth is a hypothesis, not a result.

Whether a free-text message states a known fact is not a pure lookup.
That check is part of the query reading and must be scored against a hand-checked sample.

Repeating a decision also works on a prompt trace by editing text.
The repeat is the ground truth for whether a record was used.
It is not, by itself, a difference between the two forms of evidence.

## References

- **Related Tenets**: interpretability-and-traceability, provenance-and-accountability, data-first-shared-model, model-agnostic-core
- **Related Requirements**: REQ-0006, REQ-0007, REQ-0009, REQ-0015, REQ-0016
- **External Links**: HiddenBench (arXiv 2505.11556), The Traitors (arXiv 2505.12923), TraceElephant (arXiv 2604.22708)

## Progress Updates

### 2026-11-15

Requirement drafted after the scripted Hidden Profile study showed that session records answer link questions which component logs miss.
A literature check found the outcome benchmarks and the failure-attribution benchmarks already published.
The open part is answering the cross-agent questions on those runs by lookup.
CIP-0017 holds the study design.

### 2026-11-15

CIP-0017 was accepted.
Status moved to In Progress.
No backlog tasks exist yet.
CIP-0016 is the precondition.

### 2026-11-15

Four CIP-0017 backlog tasks now exist.
All four wait on the CIP-0016 tasks.

### 2026-11-16

The scripted Hidden Profile run checks the links, and a decision can be repeated with records withheld or added.
The judge can be asked the same questions from traces and from records.
The model-backed campaigns are still open.
Status stays In Progress.
