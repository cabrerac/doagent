---
id: "2026-10-07_werewolf-information-flow-validation"
title: "Apply validated information-flow measures to Werewolf"
status: "Proposed"
priority: "Medium"
created: "2026-10-07"
last_updated: "2026-10-07"
category: "features"
related_cips:
- "0015"
- "0014"
owner: "Christian Cabrera"
dependencies:
- "2026-10-07_controlled-observability-campaign"
- "2026-10-07_llm-information-flow-validation"
tags:
- backlog
- extension
- werewolf
- external-validity
---

# Task: Apply Validated Information-Flow Measures to Werewolf

## Gating Note

This extension is subject to successful completion of the core campaign and the LLM validation task.
It remains Proposed until Gate 5 confirms that the validated measures and decoders can be transferred without redefining them around Werewolf outputs.
No new Werewolf server pair should run before that decision.

## Description

Use Werewolf as a realistic external-validity case for the validated recording-policy evaluation.
Adapt only the neutral event mapping, query instances, and environment-specific variables required by the existing measurement contract.
Preserve the finished pair 1 pilot as historical evidence rather than treating it as part of the new scored campaign.

## Motivation

The controlled environment cannot represent all properties of a natural-language multi-agent game.
Werewolf adds hidden roles, private information, strategic deception, conflicting goals, public and private communication, changing populations, and variable-length trajectories.
These properties test whether the controlled findings survive a more realistic setting.

## Justification

Werewolf was defined independently of DOAgent and therefore provides a useful external scenario.
It is unsuitable for validating estimators from scratch because trajectories are expensive and irregular.
It becomes useful after the measurement protocol is validated elsewhere.

## Scope

The extension evaluates representation and analysis of Werewolf histories.
It does not claim that DOAgent causes better gameplay, more cooperation, or different emergence.

Potential query instances include:

- recipients of private and public outcomes
- observations available before a decision
- actor and action associated with a transition
- recorded enabler links
- temporal order of selected events
- fact accessibility under validated semantic rules

Belief queries are included only if every player reports the same structured beliefs under every recording condition.

## Execution Plan

1. Review the validated core query and evidence contracts.
2. Map Werewolf roles, phases, messages, decisions, and outcomes into neutral events.
3. Identify queries that transfer without changing their definitions.
4. Reject queries that require unvalidated natural-language inference.
5. Decide whether structured role beliefs are scientifically necessary.
6. If beliefs are added, apply identical prompts and outputs to every recording policy.
7. Define truth generation independently of every analysed artifact.
8. Define fixed access conditions for player logs, structured traces, and DOAgent sessions.
9. Define parser changes before scored runs.
10. Revalidate changed parsers on synthetic Werewolf fixtures.
11. Select model, campaign size, retry policy, and exclusion rules.
12. Copy and verify the published environment dependencies on the server.
13. Freeze runners, prompts, model settings, and seeds where supported.
14. Run the predeclared campaign.
15. Report information retention, ambiguity, analysis cost, and recording cost.
16. Compare conclusions with the controlled and LLM validation studies.
17. Report where Werewolf invalidates assumptions from the controlled model.

## Acceptance Criteria

- [ ] Gate 5 explicitly authorizes the Werewolf extension.
- [ ] Every scored query was validated before the campaign.
- [ ] Werewolf neutral events are independent of recorder implementation.
- [ ] Truth is generated during play and hidden from decoders.
- [ ] Instrumentation is identical across recording policies.
- [ ] No DOAgent-only belief or explanation prompt is used.
- [ ] Service baselines include the complete log union and structured tracing.
- [ ] Pair 1 is reported only as a pilot.
- [ ] Repetition 02 from the old campaign remains excluded.
- [ ] Campaign settings and exclusions are predeclared.
- [ ] Failures and discarded games are reported.
- [ ] Results distinguish representation effects from game behaviour.
- [ ] External-validity limitations are explicit.

## Implementation Notes

Variable player populations require query answer spaces to use the living roster at each phase.
Natural-language equivalence requires a validated semantic decoder or manual annotation protocol fixed before scoring.
Protocol knowledge available to every analyst may constrain candidate sets.

The existing Werewolf code is reused only after a parity review against the neutral event and instrumentation contracts.

## Related

- CIP: 0015
- CIP: 0014
- Requirement: REQ-0015

## Progress Updates

### 2026-10-07

Task proposed as a gated external-validity study that supersedes an immediate rerun of the old server campaign.
