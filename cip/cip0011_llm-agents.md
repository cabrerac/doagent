---
author: "Christian Cabrera"
created: "2026-07-28"
id: "0011"
last_updated: "2026-07-28"
status: "Accepted"
compressed: false
related_requirements:
- "0005"
- "0013"
related_cips:
- "0005"
- "0010"
tags:
- cip
- llm
- bounded-runs
- configuration
title: "LLM-Backed Agents: Configuration and Time Limits"
---

# CIP-0011: LLM-Backed Agents: Configuration and Time Limits

> **Note**: CIPs describe HOW to achieve requirements (WHAT).
> Use `related_requirements` to link to the requirements this CIP implements.

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [ ] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

## Summary

Make LLM-backed agents practical to run and easy to set up. The library gains time limits that work for any decision
engine, plus a hook so users can supply their own rule. The examples keep all provider code but get one place to
declare provider and model. Addresses REQ-0013 (bounded runs) and the configuration side of REQ-0005
(model-agnostic core).

## Motivation

Two problems make LLM-backed agents harder to adopt than they should be. Both were found during the review of the
notebook and LLM integration work on 2026-07-28.

**Runs can hang.** There is no timeout, retry, or concurrency anywhere in the LLM path. `create_llm_tool` calls the
provider SDK with no time limit, agents decide one after another, and the gridworld demo runs 100 rounds. One slow
response stalls everything, and nothing caps total run time. A first-time user meets this before they see anything
the library is good at.

**Configuration is split across two places.** The model is set in YAML (`model: "gpt-4o"`), but the provider is
chosen in Python — the runner calls `create_llm_tool()`, which quietly defaults to OpenAI. Put a Gemini model name in
the config and you still get an OpenAI client and a confusing failure. The repository history shows this friction:
two commits titled "changing to gemini flash model", with `gpt-4o` in place again afterwards. On top of that, each
provider accepts two environment variable names, and the notebooks re-implement the LLM tool inline instead of
importing the helper, so the same setup logic lives in three places and can drift apart.

**A research angle, not just a fix.** Once a run has a time budget, the budget becomes something to study. Agents can
be compared when they must answer fast and when they may take their time — react versus reflect. The records already
hold most of what that needs: each tool call carries `elapsed_s`, Level 2 keeps the reasoning text, and the choice
status already separates act, abstain, and error. A tight budget may also make agents abstain more often, which
connects to the existing IDK work. These experiments belong to CIP-0010; this CIP only makes them possible.

## Detailed Description

### The constraint that shapes the design

The library must not depend on any provider SDK. That is the `model-agnostic-core` tenet, and it is why
`examples/llm_policy.py` states it has zero library dependency. But a timeout is a runtime concern that example code
cannot fully solve, because only the library sees every decision and writes the records.

Options considered:

- **Option A — keep everything in the examples.** Add a timeout inside `create_llm_tool` and fix the config there.
  Cheap and it respects the tenet, but every user who writes their own policy has to build the same thing again, and
  nothing bounds a whole run.
- **Option B — ship provider adapters in the library** (a `doagent.llm` module). Best first-run experience, but it
  puts provider SDKs behind the library and breaks the model-agnostic tenet. Rejected.
- **Option C — split by concern.** The library gets time limits that know nothing about models or providers. The
  examples keep every line of provider code but gain a single place to configure it.

We select **Option C**. The library learns about *time*, not about LLMs.

### What the library provides

**Built-in limits, set as plain numbers.** Two values in `run_config`: a limit for a single decision and a limit for
the whole run. Defaults keep current behaviour, so existing runs are unaffected.

**A hook for user-supplied rules.** Users who need a different rule — a spending cap, a per-agent quota, a limit on
the number of model calls — can pass their own object instead. This follows the pattern the library already uses for
`participation_registry`, `state_hash_fn`, and policies: a sensible default with an escape hatch. The hook should
stay small; one simple protocol, not a framework.

**The library always writes the record.** Whoever decides to stop, the library records it. This is the reason to do
this in the library rather than leaving it to user code: a user-side timeout produces nothing to inspect unless the
user remembers to record it, while a library-side one is recorded the same way every time. A decision that was cut
short is still a decision, and it should be traceable.

**Being cut short reuses the existing shape.** No new status value. `choice.status` stays `"error"` and
`choice.error` carries the detail, for example that the decision passed its time limit. The data model in
`docs/data-model-spec.md` already defines `choice.error` as optional detail for the error status, so nothing changes
there.

**The remaining budget is visible to policies.** The decision request should carry how much time or budget is left,
so a policy can choose to answer briefly or to think longer. Without this, only a hard cut-off is possible, and the
react-versus-reflect comparison cannot be run: the agent would never know it was under pressure. This is a small
addition that is easy to miss if only the cut-off is designed.

**Users stay in control.** The user chooses the numbers; the library only enforces what was asked for, the same way
it applies the logging level. This keeps the split described in `docs/library-boundaries.md`, which may need one
extra line noting that run configuration can include timing limits.

### What the examples provide

**One place for provider and model.** The provider moves into the YAML next to the model, so
`create_llm_tool(provider=...)` is driven by config instead of a hardcoded default. Setting a Gemini model then gives
a Gemini client.

**One implementation of the tool.** The notebooks import `create_llm_tool` rather than repeating it inline, so the
setup logic exists once.

**A timeout passed to the SDK.** Example-level, in addition to the library limit, so a stuck HTTP call fails quickly
instead of relying only on the outer limit.

### Boundaries with other CIPs

- **CIP-0005** owns the agent interface contract. If the decision request grows a "budget left" field, that change is
  agreed here but must stay consistent with the request and response payloads defined there.
- **CIP-0010** owns validation experiments, including the react-versus-reflect study. This CIP does not run
  experiments.
- **CIP-0002** owns the shared data model. This CIP deliberately avoids changing it by reusing `choice.error`.

## Implementation Plan

1. **Library: time limits**
   - Add limits for a single decision and for a whole run to `run_config`, with defaults that preserve today's
     behaviour.
   - Enforce them where the session already wraps decisions.
   - Record a cut-short decision as `choice.status: "error"` with detail in `choice.error`.

2. **Library: user hook**
   - Define one small protocol for a user-supplied limit rule.
   - Accept it in session config alongside the built-in numbers, following the `participation_registry` pattern.
   - Keep the recording in the library regardless of which rule decides to stop.

3. **Library: budget visible to policies**
   - Include the remaining time or budget in the decision request so policies can adapt.
   - Keep it consistent with the payloads defined in CIP-0005.

4. **Examples: single-source configuration**
   - Move `provider` into the YAML next to `model`, and drive `create_llm_tool` from it.
   - Pass a request timeout to the provider SDK.
   - Reduce the accepted environment variable names, or document clearly why two exist per provider.

5. **Examples and notebooks: remove duplication**
   - Import `create_llm_tool` in the notebooks instead of repeating it inline.

6. **Documentation**
   - Add a line to `docs/library-boundaries.md` noting that run configuration can include timing limits.
   - Document the limits and the hook where run configuration is described.

## Backward Compatibility

Additive. The limits default to today's behaviour, so existing runs are unchanged and no record format changes,
because being cut short reuses `choice.status: "error"` and the optional `choice.error` field. Adding the remaining
budget to the decision request is a new optional field that policies may ignore. The example configuration gains a
`provider` key; configurations without it keep the current default.

## Testing Strategy

- A policy that sleeps past its limit produces an error decision and the run finishes.
- A run that exceeds the whole-run limit stops in a controlled way and the outcome is inspectable.
- A user-supplied rule stops a run and produces the same kind of record as the built-in one.
- A policy can read the remaining budget from the decision request.
- Configuring a provider in YAML builds a client for that provider.
- No provider SDK is imported by the library, only by example code.

## Related Requirements

This CIP addresses the following requirements:

- [REQ-0013: Bounded Runs and Decision Time Limits](../requirements/req0013_bounded-runs.md)
- [REQ-0005: Model Agnostic Agent Core](../requirements/req0005_model-agnostic-agents.md) — the configuration side,
  where the split between provider and model works against staying model-agnostic in practice.

Specifically, it implements solutions for:

- Runs that never finish when a decision engine does not respond.
- Limits that users can set, replace with their own rule, and read back from the records.
- Configuration that lives in one place instead of being split between YAML and Python.

## Implementation Status

- [ ] Library: decision and run time limits in `run_config`
- [ ] Library: cut-short decisions recorded via `choice.status: "error"`
- [ ] Library: hook for user-supplied limit rules
- [ ] Library: remaining budget visible in the decision request
- [ ] Examples: provider and model configured in one place
- [ ] Examples: request timeout passed to the provider SDK
- [ ] Notebooks: import `create_llm_tool` instead of repeating it
- [ ] Docs: timing limits noted in `library-boundaries.md` and run configuration docs

### Discussion items / Future iteration

- [ ] Retries and backoff for transient provider failures — related to limits but a separate concern.
- [ ] Running agent decisions concurrently, which would change how a whole-run limit is measured.
- [ ] A `doagent.analysis.temporal` submodule alongside the existing four, for studying time spent against outcome
      quality.

## Progress Updates

### 2026-07-28 (accepted)

CIP moved to **Accepted** and broken into six backlog tasks:

- `2026-07-28_run-config-time-limits` — the two limits and the cut-short record (do first)
- `2026-07-28_user-limit-rule-hook` — user-supplied rules; depends on the limits landing
- `2026-07-28_budget-in-decision-request` — remaining budget visible to policies; must fit CIP-0005 payloads
- `2026-07-28_single-source-llm-provider-config` — provider and model in one place, plus an SDK timeout
- `2026-07-28_notebooks-import-llm-tool` — remove the duplicated LLM tool from the notebooks
- `2026-07-28_document-timing-limits` — run-config docs and the one line in `library-boundaries.md`

The two example-side tasks (provider config, notebook cleanup) have no dependency on the library work and remove most
of the setup friction on their own.

### 2026-07-28

CIP created. Design agreed in discussion: the library handles time, the examples handle providers; built-in limits
plus a hook for user rules; the library writes the record either way; being cut short reuses `choice.status:
"error"`; the remaining budget is visible to policies so react-versus-reflect can be studied later. Requirement
REQ-0013 created for the bounded-runs outcome, with REQ-0005 linked for the configuration overlap.

## References

- `examples/llm_policy.py` — `create_llm_tool` and `llm_decide_factory`
- `docs/data-model-spec.md` — choice shape, `choice.error`, tool steps with `elapsed_s`
- `docs/library-boundaries.md` — user versus library responsibilities
- `backlog/features/2026-03-28_notebook-restructuring-llm-integration.md` — where both problems were recorded
