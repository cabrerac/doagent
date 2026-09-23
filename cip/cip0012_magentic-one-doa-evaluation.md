---
author: "Christian Cabrera"
created: "2026-09-15"
id: "0012"
last_updated: "2026-09-23"
status: "In Progress"
compressed: false
related_requirements:
- "0014"
- "0002"
- "0003"
- "0005"
- "0006"
- "0007"
related_cips:
- "0002"
- "0003"
- "0010"
- "0011"
tags:
- cip
- validation
- evaluation
- llm-mas
- magentic-one
- reproducibility
title: "LLM MAS Attribution Evaluation (Small Team First, Magentic-One Stretch)"
---

# CIP-0012: LLM MAS Attribution Evaluation (Small Team First, Magentic-One Stretch)

> **Note**: CIPs describe HOW to achieve requirements (WHAT).
> Use `related_requirements` to link to the requirements this CIP implements.

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [x] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

## Summary

Evaluate failure attribution (who / when) on **DOAgent-hosted teams** for AAMAS (REQ-0014). **D** is native DOAgent records. **W** and **T** are independent baselines (Who&When-style output log and TraceElephant-static interceptor). They live under `experiments/attribution/baselines/` and are not part of `doagent/`.

Two tables, never mixed:

1. **Attribution (paired).** One execution: DOAgent writes D; observe-only collectors write W and T. Judges run on those three packs against that run’s gold. Lookup on D only.
2. **Capture cost (unpaired).** Five executions — W-only / T-only / live D0 / D1 / D2 — measuring time and capture-log bytes. No judges in that clock. Do not require the five failures to match.

Zhang/Chen-style **LLM judges** (all-at-once, step-by-step, binary search) score W, T, D0, D1, and D2. Repeat paired runs and each cost condition when teams are stochastic. W and T come from collectors, not from reshaping D.

**Paper-minimum (Phase 1):** a **small** DOAgent team (about 2–3 agents, at most one thin tool — not a browser). Planted \((i^*, t^*)\). This evaluation **goes in the paper**.

**Stretch (Phase 2):** Magentic-One roles and **real** specialist tools on current DOAgent APIs. Specialists are Microsoft’s AutoGen agents. Coordination stays on the Session store. **If it lands in time**, it becomes the paper’s main instance and Phase 1 is reported as a **proof of concept**. If it does not, Phase 1 remains the paper eval. Magentic-One is **not** removed from this CIP.

**Library-first constraint:** implement using **current** DOAgent Session, topology, participation, recording levels, and analysis APIs. If something required for a paper-usable run is missing, **stop and open a new requirement and/or CIP**.

**Which requirements?** Primary: REQ-0014. Also exercises shared data (REQ-0002 / CIP-0002), decentralisation spectrum (REQ-0003 / CIP-0003), model-agnostic agents (REQ-0005 / CIP-0011), interpretability and traceability (REQ-0006 / REQ-0007).

## Motivation

Who&When (Zhang et al., ICML’25) asks who failed and at which step, mostly from **output-only** logs. TraceElephant (Chen et al., ACL 2026) shows that **full step inputs and outputs** (plus optional replay) improve that task, via an API interceptor around existing systems. Neither paper makes the shared data model the **coordination interface**.

Our claim is not “we beat their published tables” and not “we generate their datasets.” It is: a data-oriented store **D** is a first-class evidence pack for the same who/when question, and we can measure both **attribution quality** and **capture cost** against conventional W and T collectors that do not live in the library.

A full Magentic-One port is the strongest inhabited instance but is **too large as the only gate** for the AAMAS date. A small planted team is enough to freeze the protocol. Magentic-One stays the stretch.

Gridworld and push remain fast development checks. They are not the paper’s primary LLM MAS result.

## Detailed Description

### Design principles

1. **Phase 1 first.** Small team + planted gold + W/T/D + judges + lookup + costs. Paper-complete without Magentic-One.
2. **Magentic-One kept, not required.** Same mapping as before. Phase 2 reuses AutoGen specialist agents and tools. The store remains the mailbox. If it lands, it leads the paper and Phase 1 is the PoC.
3. **Current DOAgent first.** `Session.from_config`, topology, `decision_context`, `visible_participants`, `record_update` / `agent_update`, logging levels 0–2, `inspect`, participation.
4. **Gap → new REQ/CIP.** No private validation protocol that pretends to be a library feature.
5. **Paired attribution, unpaired cost.** Do not score W from one seed against T from another. Do not put judge time in the capture-cost clock. Do not compare to Zhang/Chen published accuracies as a controlled arm. Do not use their gold on our new runs.
6. **Baselines stay outside the library.** W and T collectors live under `experiments/attribution/baselines/` (`who_when/`, `trace_elephant/`). They observe; they do not feed the team.
7. **Recording policy ≠ “all information.”** D holds what the logging level kept.
8. **Shared step clock.** W, T, and D must agree on what “when” means (Phase 1: 0 assign, 1 solve, 2 check).

### Phase 1 — small DOAgent team (paper-minimum)

**Team (illustrative; freeze in the run README):** e.g. planner/orchestrator + solver, or planner + one tool specialist (calculator or search **stub**, not Chromium). Federated hub + one leaf is enough if it matches Magentic-One’s *control pattern* at toy scale.

**Gold:** planted decisive error \((i^*, t^*)\) on each scored run. Natural-failure annotation is optional later.

**Evidence packs:**

| Pack | Approx. paper | How it is collected | Contents |
|---|---|---|---|
| **W** | Who&When | `experiments/attribution/baselines/who_when` (output logger) | Ordered `{step, agent, content}` utterances; no step input |
| **T** | TraceElephant *static* | `experiments/attribution/baselines/trace_elephant` (step I/O interceptor) | Per-step **input** \(x_t\) + **output** \(y_t\), agent id; task-facing fields only |
| **D2 / D1 / D0** | — | Live D2 Session; D1/D0 projected from that run for accuracy, or live D0/D1/D2 for cost | Native records at logging level 2, 1, or 0 |

We do **not** implement TraceElephant’s **dynamic** arm (counterfactual re-run from step \(t\)) in Phase 1. Record replay of history ≠ intervention.

NoOp is not the capture-cost baseline. This team coordinates through the store, so a discard-all adapter cannot run the same protocol. NoOp is also not “the team without DOAgent.”

**Attribution — paired, one execution:**

1. Run the team once at logging level 2. DOAgent writes D2. Observe-only W and T collectors write their packs from that same run. Project D0 and D1 from D2.
2. **Same LLM judges** on **W, T, D0, D1, and D2**. Hypothesis to *test*: D2 ≷ D1 ≷ D0 and D ≷ T > W.
3. **Lookup on D2** only. Report next to the judges, not as a fourth prompting style.

**Capture cost — unpaired, five executions, no judges:**

1. W-only — same policies, **no DOAgent**. The host loop passes each return value to the next agent. W only logs outputs.
2. T-only — same as (1), with the T interceptor recording step input and output.
3. Live D0, D1, and D2 — agents coordinate through the shared store at that logging level.

W and T are not the mailbox. Time includes writing the capture log. Bytes count only that log. Do not require those five runs to share gold.

**Stochastic teams:** repeat the paired run for a distribution of attribution scores; repeat each cost condition for a distribution of time and bytes.

**Paper figures (Phase 1):** (1) who/when for LLM judges on paired W vs T vs D0/D1/D2; (2) lookup vs those methods (accuracy + judge tokens); (3) capture cost of W vs T vs live D0/D1/D2.

### Phase 2 — Magentic-One on DOAgent (stretch; agreed 2026-09-20)

Phase 1 live campaign `attribution_campaign_20260920_193358` is in. Phase 2 stand-in campaigns ran on 2026-09-23. The capital plant did not favour DOAgent. The crate plant (`attribution_campaign_20260923_004741`) sat at the ceiling because the plan stated the grading rule. Next session starts from a case as close as possible to a Who&When dataset execution. Whether a fully described dataset execution can be reproduced here is still open. Do not copy published mistake indexes onto a new log.

**Same failure type, not their labelled instance.** Reuse a versioned Who&When / GAIA / AssistantBench **query**. Aim at the same **kind** of failure (wrong web fact, orchestrator accepts). Do **not** copy published `mistake_agent` / `mistake_step`. Those indexes belong to an AutoGen log we are not replaying. After our run, write **new** gold (planted or newly annotated).

**Reuse their agents and tools, not their group chat.**

| Reuse | Do not reuse |
|---|---|
| `MultimodalWebSurfer` (Chromium / Playwright) | `MagenticOneGroupChat` (that class **is** their mailbox) |
| `FileSurfer` | Published Who&When / TraceElephant gold on our new transcript |
| `MagenticOneCoderAgent` | Stub specialists that invent a fake page |
| `CodeExecutorAgent` as ComputerTerminal | Wrapping AutoGen as the coordinator and treating D as a sidecar |

Each specialist is a long-lived AutoGen object, wrapped as a Session policy. A dedicated event loop calls `on_messages` so the browser, file workspace, and shell stay open across turns. The Session records the action that policy returns. The orchestrator is ours. The task ledger rides on the assign action (`facts`, `guesses`, `plan`). The progress ledger rides on the accept action (`is_complete`, `reason`, `next_agent`, `stall_count`). `decide` stores both. A thin turn-clock env advances the shared step. W and T only watch.

**Gold modes** (config):

- `accept_last` — after the first specialist result, the orchestrator stops. Used for offline tests and a smoke campaign so recoverability gold is known (orchestrator at that accept step).
- `none` — live run may fail on its own. Annotate `gold.json` after the fact.

Do not write “correct is …” into D2 explanations.

**Judge.** `gold.json` stores `roster`. The judge inserts those names into the shared recoverability prompt. The addition team stores orchestrator, solver, and checker. This team stores all five roles, including specialists that stayed idle. A run with no roster raises.

**Dependencies.** Optional extra (`autogen-agentchat`, `autogen-ext[magentic-one,openai]`, Playwright Chromium). Offline tests use scripted stand-ins. CI does not need a browser.

**Same protocol as Phase 1.** Paired attribution (one execution, D + observe-only W/T). Unpaired capture cost (W-only / T-only host loop without Session; live D0/D1/D2). Magentic-One becomes the **main** paper instance if it lands. Phase 1 is then the proof of concept.

**Tree** (2026-09-22):

- In `experiments/magentic_one/`: `query.py`, `team.py`, `direct.py`, `specialists.py`. Frozen query `capital-of-france`. Accept-last gold is the orchestrator at step 2. Planted web fact is Lyon.
- `specialists.py` wraps an `on_messages` agent as a Session policy. Tests pass a stand-in. The four AutoGen classes are not constructed yet.
- Optional extra `magentic-one` in `pyproject.toml`.
- Still to add: `config.yaml`, campaign `--team magentic_one`, gold mode `none`.

CaptainAgent-generated teams stay deferred.

### Magentic-One → DOAgent mapping (Phase 2; also a pattern for Phase 1)

**Topology:** federated. `orchestrator` is hub. Specialists are leaves.

| Magentic-One | DOAgent `agent_id` | Capabilities (participation) |
|---|---|---|
| Orchestrator | `orchestrator` | `plan`, `assign`, `replan` |
| WebSurfer | `web_surfer` | `browser` |
| FileSurfer | `file_surfer` | `files` |
| Coder | `coder` | `code` |
| ComputerTerminal | `computer_terminal` | `shell` |

**Shared data (no parallel private log):**

| Magentic-One concept | DOAgent mechanism | Suggested `payload_type` / content |
|---|---|---|
| Task Ledger (facts, guesses, plan) | Orchestrator `agent_update` or `record_update` | `task_ledger` — `{facts, guesses, plan, version}` |
| Progress Ledger | same | `progress_ledger` — `{is_complete, reason, next_agent, instruction, stall_count}` |
| Subtask assignment | Orchestrator decision `choice` and/or progress ledger | `assign` — `{assignee, instruction}` |
| Specialist result | that agent’s `agent_update` | `web_result` / `file_result` / `code_artifact` / `shell_result` |
| Tool steps | Level 2 tool reasoning steps when tools are configured | automatic capture where supported |
| Browser / files / shell world | `environment_outcome` + `trace` | observations after acted steps |
| Team membership | `participation` (+ default hub roster hook) | join/leave/roster as needed |

**Reads:** Orchestrator uses `decision_context` and `visible_participants`. Specialists read the latest assignment / progress ledger aimed at them.

**Run loop (outer/inner):** query → `task_ledger` → assign one specialist or done → result `agent_update` → on stalls, replan → stop on complete, `max_turns`, or `max_stalls`.

Phase 1 may use a **cut-down** of this loop (two roles, short max turns).

Logging level **1+** for who/provenance; **2** when step-level “when” needs tool traces.

### What current DOAgent already covers

- Federated hub + leaves, `on_hub_membership` / roster visibility.
- `decision_context` / `visible_records` / `visible_participants`.
- `agent_update` with decision choice, optional explanation/reasoning by level.
- `record_update` for hub-authored summaries.
- Participation registry and `participation` records.
- File / in-memory / NoOp adapters (NoOp is not the paper cost baseline for this team).
- Analysis / inspect for post-hoc attribution.
- LLM-backed agents and bounded-run concerns (CIP-0011).

### Likely gaps (open REQ/CIP if blocking)

| Gap | Phase | If needed, open |
|---|---|---|
| Independent **W / T collectors** | 1 | Keep under `experiments/attribution/baselines/`; not library |
| Judge harness (all-at-once / step-by-step / binary search) | 1 | Validation/experiment code first |
| Lookup rules that are more than `actor` + step id | 1 | Document in run README; library CIP only if reused |
| Built-in assign-one-agent / stall / replan helpers | 2 | Prefer validation helper |
| First-class ledger **kinds** | 2 | REQ + CIP on data model |
| Production WebSurfer | 2 | Reuse AutoGen `MultimodalWebSurfer` as a Session policy. Open a library CIP only if Session cannot host a long-lived async agent. |
| TraceElephant **dynamic** replay / counterfactual | neither required | Separate CIP if claimed |

Rule: **scenario policies and stubs live under validation/examples**; **shared abstractions** become library CIPs.

### What we will not claim

- Cross-corpus comparison to Zhang or Chen published accuracies as the main result.
- That D contains “all” information (only the recording policy).
- That lookup **will** beat LLM judges (we measure it).
- That W/T collectors **are** Who&When / TraceElephant the datasets.

### Reproducibility artefacts

Under `experiments/attribution/` for Phase 1 (and a sibling experiment for Phase 2):

1. **Query / plant pack** — Phase 1: small frozen tasks + planted-error specs. Phase 2: versioned GAIA / AssistantBench / Who&When Magentic-One IDs.
2. **Pinned config** — models, limits, logging level, topology, live AutoGen tools vs test stand-ins.
3. **Entry script(s)** — paired D+W+T run; separate D / W-only / T-only cost runs.
4. **Gold** — planted (and optional annotation) keyed by `run_id`.
5. **Judge + lookup scripts** — pinned judge model; lookup rule documented.
6. **Run manifest** — `run_id`, git commit, timestamps, config hash.
7. **Fidelity statement** — Phase 1 team description; Phase 2: AutoGen specialists + DOAgent mailbox, not MagenticOneGroupChat.

### Alternatives considered

| Option | Decision |
|---|---|
| Magentic-One as the only paper eval | Rejected as the **gate**; kept as **stretch** |
| Small team only, delete Magentic-One from CIP | Rejected; mapping and Phase 2 stay |
| Offline reshape of published Who&When / TraceElephant logs only | Not the main eval (no live D); optional footnote |
| Dual implementation (AutoGen Magentic-One vs DOAgent) as Phase 1 | Deferred; too heavy. Phase 1 is **one** team; W/T are collectors, not a second MAS |
| Wrap `MagenticOneGroupChat` and log into D | Rejected. D would be a sidecar. The store would not be the mailbox. |
| Phase 2 with stub specialists only | Rejected 2026-09-20. Agents and tools must match the baseline implementations. |
| W/T only as post-hoc exports of D | Rejected for the paper tables; collectors are the W/T packs |
| NoOp as “without DOAgent” / capture-cost baseline | Rejected for this team (store is the coordination channel) |
| MultiAgentBench / ASC full metric suite | Rejected (wrong metrics / no dataset) |
| Gridworld as primary paper env | Rejected; dev harness only |
| Compare only to published Zhang/Chen numbers | Rejected (cross-corpus) |

## Implementation Plan

1. **Phase 1 gap audit** — walk 2–3 agents through Session APIs; list blockers → REQ/CIP or stub.
2. **Phase 1 scaffold** — small team, planted error, file-backed D, YAML + README.
3. **W / T projections + lookup** — development check from D (done).
4. **LLM judges** on W, T, D; token accounting (done).
5. **Manifests** (done).
6. **Independent W and T baselines** under `experiments/attribution/baselines/{who_when,trace_elephant}`.
7. **Paired attribution run** and **unpaired capture-cost runs**; repeats when needed.
8. **Phase 1 paper-ready** — figures/tables for AAMAS even if Phase 2 never starts.
9. **Phase 2** — Magentic-One roles, AutoGen specialist tools, orchestrator and ledgers on the Session store, same paired/unpaired protocol. Then treat Phase 1 as PoC in the paper if Phase 2 lands.
10. Update REQ-0014 acceptance when Phase 1 (and Phase 2 if any) is validated.

## Backward Compatibility

No breaking change to existing demos. New validation code is additive. Library changes only via separate accepted CIPs.

## Testing Strategy

**Phase 1**

- Collectors: W has no step inputs that T has; T has \(x_t, y_t\) on the shared step clock.
- Observe-only W/T on a D run do not change planted gold.
- Planted \((i^*, t^*)\) recoverable by lookup on D.
- LLM judges run on all three packs without crashing on fixture traces.
- Capture-cost runs time the team plus one collector and do not call judges.

**Phase 2 (if built)**

- Ledger updates visible under federated topology; only assignee acts per inner-loop step.
- Offline tests use stand-in specialists (no Playwright, no API key).
- Same paired-attribution / unpaired-cost smoke as Phase 1 on a Magentic-One–style run.

## Related Requirements

- [REQ-0014](../requirements/req0014_magentic-one-style-evaluation.md) — primary outcome (title still Magentic-One–centric; protocol is W/T/D, small team first).
- [REQ-0002](../requirements/req0002_shared-data-model.md), [REQ-0003](../requirements/req0003_decentralisation-spectrum.md), [REQ-0005](../requirements/req0005_model-agnostic-agents.md), [REQ-0006](../requirements/req0006_interpretability.md), [REQ-0007](../requirements/req0007_traceability.md) — exercised by the eval.

## Implementation Status

- [x] Design documented (this CIP, Proposed)
- [x] Eval protocol revised: W / T / D, LLM judges + lookup, costs; Phase 1 vs Phase 2 (2026-09-18)
- [x] Accepted; Phase 1 started (2026-09-18)
- [x] Phase 1 gap audit against current Session APIs (no new core REQ)
- [x] Phase 1 small-team scaffold + planted gold (`experiments/attribution/`; gold = checker / step 2)
- [x] W / T export from D with documented projection rules (2026-09-19)
- [x] Structured lookup on D recovers checker / step 2 (2026-09-19)
- [x] GPT-4o judge harness on W, T, and D: all-at-once, step-by-step, binary search (2026-09-19)
- [x] Token accounting, manifests, and evaluator timing of the addition-team run (2026-09-20)
- [x] Protocol revised: independent W/T baselines; paired attribution; unpaired capture cost (2026-09-20)
- [x] Independent W and T collectors under `experiments/attribution/baselines/{who_when,trace_elephant}` (2026-09-20)
- [x] Paired D+W+T attribution run and unpaired D / W-only / T-only cost runs (2026-09-20)
- [x] Paper-shaped collector packs; judges score collectors not D projections; runner has separate cost and accuracy tables (2026-09-20)
- [x] Capture cost: W, T, live D0/D1/D2; bytes are the capture log only; D0/D1 accuracy views projected from D2 (2026-09-20)
- [x] Removed W/T projections; judges read collector packs only (2026-09-20)
- [x] Recoverability judge prompt; paper plot labels; campaign progress and auto-plots (2026-09-20)
- [x] Phase 1 live campaign `attribution_campaign_20260920_193358` (cost 10, judge 10)
- [x] Phase 2 design: real AutoGen specialists, Session mailbox, new gold (2026-09-20)
- [x] Phase 2 stand-in team, direct host, and W/T collectors on one step clock (2026-09-22)
- [x] Judge roster read from `gold.json` (2026-09-22)
- [x] `on_messages` policy wrapper and optional `magentic-one` extra (2026-09-22)
- [x] Four AutoGen specialist classes construct. One live browser smoke wrote gold and packs (2026-09-23)
- [x] Recorded runs write D0, D1, and D2. Campaign `--team magentic_one` runs the stand-in (2026-09-23)
- [x] Crate plant campaign `attribution_campaign_20260923_004741` (cost 10, judge 10). Scores at the ceiling (2026-09-23)
- [ ] Who&When-shaped scenario. Settle whether a described dataset execution can be replayed before coding the plant
- [ ] Phase 1 paper-ready (abstract and write-up; tables exist)
- [ ] Follow-on REQ/CIP opened for any confirmed library gaps
- [ ] REQ-0014 acceptance criteria updated when validated

## References

- Fourney et al., *Magentic-One: A Generalist Multi-Agent System for Solving Complex Tasks*, arXiv:2411.04468
- Zhang et al., *Which Agent Causes Task Failures and When?*, arXiv:2505.00212; [dataset/code](https://github.com/ag2ai/Agents_Failure_Attribution)
- Chen et al., *Seeing the Whole Elephant* (TraceElephant), arXiv:2604.22708; [code](https://github.com/TraceElephant/TraceElephant)
- [docs/validation-and-benchmarks.md](../docs/validation-and-benchmarks.md)
- [docs/data-model-spec.md](../docs/data-model-spec.md)
- [guides/doa-principles.md](../guides/doa-principles.md)
- CIP-0002, CIP-0003, CIP-0010, CIP-0011
