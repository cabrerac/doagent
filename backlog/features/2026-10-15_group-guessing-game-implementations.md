---
id: "2026-10-15_group-guessing-game-implementations"
title: "Add the group guessing game as a second environment"
status: "Proposed"
priority: "Low"
created: "2026-10-15"
last_updated: "2026-10-21"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies:
- "2026-10-15_hidden-profile-doagent-implementation"
- "2026-10-15_hidden-profile-marble-implementation"
tags:
- backlog
- environment
- gated
- information-flow
---

# Task: Add the Group Guessing Game as a Second Environment

## Description

Add a group guessing game as a second environment with the same two implementations.
Agents propose numbers that must sum to a hidden target, then hear whether the sum was too high or too low.
This is a gated task.
Do not start it until the Hidden Profile comparison has produced a result.

## Motivation

A single environment cannot tell us whether a recording difference is a property of the frameworks or a property of one game.
A second environment with a different information structure is how that is checked.

The guessing game is the natural second choice because public feedback spends a shared budget of uncertainty.
When `n` target values remain equally possible, that uncertainty is `log2(n)`.

## Justification

The paradigm comes from Riedl's study of emergent coordination in groups of language-model agents.
Agents guess numbers, and the only feedback is whether their sum was too high or too low.

Against Hidden Profile, it differs in a useful way.
Hidden Profile moves facts between agents.
The guessing game shrinks the set of targets still consistent with the public feedback.
If the two implementations differ on both, the difference is about recording.
If they differ on only one, the difference is about the game.

## Design Sketch

A hidden target is drawn from a declared numeric range.
In each round every agent proposes a number.
The environment reports that the sum was too high, too low, or exact.
The episode ends when the sum matches the target or the round budget runs out.

The scripted policy proposes numbers from the targets still consistent with the feedback, so the same seed repeats the same guesses.

Measurable quantities:

- Hartley ambiguity of the target values still consistent with the feedback
- marginal entropy of each agent's guess
- joint entropy of all guesses in the same round
- multi-information across those guesses
- relative entropy from each agent's belief to the posterior over the remaining targets
- time-delayed mutual information between agents' guesses across rounds

The recording question is whether the artifacts let a decoder reconstruct the remaining targets after each round.
That requires knowing each guess, the feedback, and which agents heard it.

The same split applies: rules and policies framework-independent, then one DOAgent session and one MARBLE run.

## Gate

Do not begin until all of the following hold.

- [ ] Both Hidden Profile implementations pass Gate 3 on implementation fairness.
- [ ] The Hidden Profile comparison has produced a scored result.
- [ ] That result is understood well enough to say what a second environment would test.

A second environment started before the first has produced a result doubles the work without answering anything.

## Acceptance Criteria

Deferred until the gate opens.
Writing acceptance criteria now would fix decisions the first result should inform.

## Implementation Notes

The connection to the theoretical framework is a motivation, not a deliverable.
Do not claim the game instantiates the information isolation axiom.
It shares the structure of a total information budget being spent, and that is what makes it interesting.

## Dependencies and Gate

Blocked on both Hidden Profile implementation tasks and on a scored first result.

## Related

- CIP: 0015
- Requirement: REQ-0015

## Progress Updates

### 2026-10-15

Task created as a gated follow-up so the second environment cannot start before the first produces a result.

### 2026-10-21

The design sketch now matches the plan.
Agents guess numbers that must sum to a hidden target and hear whether the sum was too high or too low.
The uncertainty of the values still consistent with that feedback is `log2` of how many remain.
