---
id: "0013"
title: "Bounded Runs and Decision Time Limits"
status: "Proposed"
priority: "High"
created: "2026-07-28"
last_updated: "2026-07-28"
related_tenets:
- "library-first"
- "interpretability-and-traceability"
- "model-agnostic-core"
stakeholders:
- "library users"
- "agent developers"
- "researchers"
tags:
- requirements
- bounded-runs
- llm
---

# REQ-0013: Bounded Runs and Decision Time Limits

> **Remember**: Requirements describe **WHAT** should be true (outcomes), not HOW to achieve it.

## Description

A run must always finish. Today a slow or unresponsive decision engine can stall a run with no way to stop it
cleanly, because nothing limits how long a single decision or a whole run may take. This is most visible with
LLM-backed policies, where one call can hang, but it applies to any slow decision engine or tool.

Users should be able to say how long a decision may take and how long a run may take, and the run should respect
those numbers. When a limit is reached, the run should stop in a controlled way and leave a record of what happened,
rather than hanging or failing silently. Users who need a different rule (for example a spending cap or a per-agent
quota) should be able to supply their own, without giving up the recording.

Agents should also be able to see how much time they have left, so a policy can choose to answer quickly or to think
longer. This makes the time limit a property agents can reason about, not only a safety net.

**Why this matters**: `library-first` — a library that can hang is hard to adopt, and users must stay in control of
their own runs. `interpretability-and-traceability` — a decision that was cut short is still a decision, so it must
be visible in the records. `model-agnostic-core` — limits are about time, not about any particular model or provider,
so they must work for any decision engine.

**Who benefits**: Library users running demos for the first time, agent developers whose policies call slow external
services, and researchers who want to vary the time budget and study how agents behave under it.

## Acceptance Criteria

- [ ] A run always terminates, even when a decision engine does not respond.
- [ ] Users can set a limit on how long a single decision may take and on how long a whole run may take.
- [ ] When a limit is reached, the outcome is recorded and can be read back with the other records.
- [ ] Users can supply their own limit rule instead of the built-in one, and it is recorded the same way.
- [ ] A policy can read how much time or budget it has left when making a decision.
- [ ] Limits work the same way for any decision engine, with no provider-specific behaviour in the library.

## Notes (Optional)

The records already carry `elapsed_s` for each tool call, so the timing data needed to study behaviour under limits
is largely present. What is missing is the ability to bound a run and to record the fact that a limit was hit.

Being cut short is expected to reuse the existing `choice.status: "error"` with an explanation in `choice.error`,
rather than a new status value, so the data model stays stable. That decision belongs to the CIP.

Studying how agents behave under different budgets ("react vs reflect") is a research use of this requirement, not
part of it. Those experiments belong under REQ-0010 and CIP-0010.

## References

- **Related Tenets**: library-first, interpretability-and-traceability, model-agnostic-core
- **External Links**: None

## Progress Updates

### 2026-07-28

Requirement drafted after a review of LLM-backed policies found no timeout, retry, or run limit anywhere in the
decision path, while the gridworld demo runs 100 rounds with sequential decisions. HOW this is achieved is designed
in CIP-0011.
