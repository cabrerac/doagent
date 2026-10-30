---
id: "0015"
title: "Quantifiable Information-Theoretic Observability"
status: "In Progress"
priority: "High"
created: "2026-10-07"
last_updated: "2026-10-30"
related_tenets:
- "data-first-shared-model"
- "interpretability-and-traceability"
- "provenance-and-accountability"
- "model-agnostic-core"
stakeholders:
- "multi-agent system researchers"
- "agent developers"
- "system operators"
- "auditors"
tags:
- requirements
- information-theory
- observability
- evaluation
---

# REQ-0015: Quantifiable Information-Theoretic Observability

## Description

Researchers must be able to quantify how much information about a multi-agent execution is retained by a recording policy.
The evaluation must distinguish information retained by the artifacts from the effort required to recover and analyse it.
It must support comparisons in which DOAgent ties with or performs worse than service-based alternatives.

The evaluated questions must cover information flow, decisions, outcomes, and their relationships.
The results must state which claims concern information content, which concern reconstruction cost, and which concern runtime overhead.

**Why this matters**: The data-first shared model should make observability measurable rather than assumed.
The interpretability, traceability, and provenance tenets require evidence that retained data supports specific questions about an execution.
The model-agnostic core requires the evaluation to work first with controlled agents and later with LLM agents.

**Who benefits**: Multi-agent system researchers, agent developers, system operators, and auditors.

## Acceptance Criteria

- [ ] A declared family of questions about an execution has measurable uncertainty before and after retained artifacts are observed.
- [ ] Information retained or lost by each recording policy is reported with information-theoretic quantities whose assumptions are explicit.
- [ ] Reconstruction effort and capture cost are reported separately from information retained.
- [ ] Comparisons use two implementations of the same multi-agent system, one coordinated through DOAgent and one built as independent services.
- [ ] Service comparisons include isolated service logs, their complete union, and a structured service baseline.
- [ ] Controlled experiments provide known probability distributions or enough repeated observations to validate estimators.
- [ ] A realistic multi-agent case study tests whether results from the controlled experiment transfer beyond its simplified setting.
- [ ] The evaluation reports ties and disadvantages without assuming that DOAgent must outperform another representation.
- [ ] Any connection to information topography identifies the probability model, state space, and limits of the comparison.

## Notes

Exact recoverability means that the answer to a declared question is a deterministic function of the retained artifacts.
Residual candidate counts may be reported as Hartley ambiguity when no probability distribution is justified.
Shannon conditional entropy and mutual information require a probability model or repeated samples from a stable process.
Analysis time, files read, joins, and parsing rules are computational measures rather than entropy measures.

## References

- **Related Tenets**: data-first-shared-model, interpretability-and-traceability, provenance-and-accountability, model-agnostic-core
- **Related Work**: Shannon, Cover and Thomas, MacKay, Schreiber, Paninski, Baez et al., and Lawrence's inaccessible game

## Progress Updates

### 2026-10-07

Requirement made Ready after the Werewolf pilot showed that complete service logs can recover the existing propagation metric.
The next evaluation must measure retained information, residual uncertainty, and analysis cost without presuming a DOAgent advantage.

### 2026-10-08

Implementation started with exact self-information, Shannon entropy, and Hartley ambiguity measures.
The first executable checks reproduce the hand-calculated three-agent delivery examples.

### 2026-10-14

Exact conditional entropy and mutual information now compare analytic recording policies through joint probability tables.
The measures remain internal experiment code and do not change the public DOAgent library.

### 2026-10-15

The comparison now requires two real implementations of the same system rather than recorders written for the study.
Recoverable information is scored against each run's private truth.
Hidden Profile is the primary environment, and the group guessing game links the measures to the inaccessible game.

### 2026-10-22

Hidden Profile now has framework-independent rules, a scripted policy, and an exact distribution over 18 deals.
The controlled runs are not scored, and the two implementations have not been built.

### 2026-10-30

The Hidden Profile campaign is scored.
All 18 deals were read at logging levels 0, 1, and 2.
The group guessing game, LLM agents, and Werewolf are not started.
