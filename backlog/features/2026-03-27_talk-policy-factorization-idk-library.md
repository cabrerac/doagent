---
id: "2026-03-27_talk-policy-factorization-idk-library"
title: "Library support for policy factorization and IDK (talk + demos)"
status: "Completed"
priority: "High"
created: "2026-03-27"
last_updated: "2026-03-28"
category: "features"
related_cips:
- "0002"
- "0003"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- talk
- agentic-reasoning
- policy-factorization
- interpretability
- decentralisation
---

# Task: Library support for policy factorization and IDK (talk + demos)

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Enable the **DOAgent library** (not only user-space wrappers) to support a **talk and live demo** aligned with:

- **`papers/agentic-reasoning-llm.md`**: POMDP-style **think-act** structure; **policy factorization** (reasoning in Z / trace, external action in A), with **observable** linkage in the shared substrate.
- **`papers/consistent-reasoning-paradox-llm.md`** (CRP): **trustworthy** behaviour includes the ability to say **"I don't know"**; the paper's **"I don't know" function** is a formal target -- this task implements **library-visible abstention / IDK outcomes** suitable for demonstration and inspection, **without** claiming full formal realisation of the CRP.

**Delivery surfaces:** slides (screenshots from `inspect` / analysis) and **`notebooks/`** for a reproducible live path. Reuse **existing scenarios** (e.g. push, gridworld) **or** add a **minimal toy env** -- decision deferred during implementation planning (Stage 3).

**Demo strategy (from discussion):** Prefer **one LLM agent** (plus heuristics if needed) as the **primary** demo for reliability; optionally a **short multi-agent** segment (e.g. topology / visibility) to tie **CIP-0003** (reasoning context from shared memory).

## Goal

- **First-class** separation in **records and/or Session API** between a **reasoning step** (Z-like) and the **external action** (A), with stable **trace/provenance** linkage -- not "factorization only in user policy code."
- **First-class** **abstention / IDK** path (structured outcome, not parse failure), **recorded** and **inspectable** at appropriate logging levels.

## Non-goals (for this task)

- Full implementation of the CRP **"I don't know" function** as defined in the paradox paper (computational / logical content beyond demonstration hooks).
- Complete **`session.memory(...)`** / reasoning-centric memory API (CIP-0002 future iteration umbrella) -- may **narrow** a minimal slice if it overlaps.
- Post-training / RL; new LLM training.

## Acceptance Criteria

- [ ] **Data model / API**: Reasoning vs action are **distinguishable** in stored records (new `kind`, structured payload fields, and/or documented two-phase write path via `RecordWriter` / `Session`) with **IDs or trace links** between reasoning and action.
- [ ] **IDK / abstain**: Policy or library path can emit an **explicit abstention** (naming TBD: e.g. `decision_type`, dedicated action value, or record flag) with **explanation** support where logging level allows; visible via **`session.inspect`** (or equivalent).
- [ ] **Tests**: Unit and/or integration tests cover **factorized write sequence** and **IDK** path; full suite passes (`python -m pytest`).
- [ ] **Notebook**: At least one **notebook** under `notebooks/` runs end-to-end (config-driven `Session`, heuristic and/or LLM policy placeholder with clear env var / optional API key).
- [ ] **Docs**: Short update to **`docs/data-model-spec.md`** (and/or **library-boundaries**) for new fields or kinds, consistent with CIP-0002.

## Implementation Notes

- Coordinate with **CIP-0002** (policy factorization, future record kinds) and **CIP-0006/7/8** if trace/provenance semantics change.
- **CIP-0003**: Multi-agent demo segment uses existing **topology / `visible_records`**; no requirement to complete distributed-store future items for this task.
- Heuristic policies can implement **degenerate** factorization (single step) to show parity with LLM two-step in the **same** API.

## Related

- **CIP:** [0002](../cip/cip0002_shared-data-model.md), [0003](../cip/cip0003_decentralisation-spectrum.md)
- **Papers:** `papers/agentic-reasoning-llm.md`, `papers/consistent-reasoning-paradox-llm.md`, `papers/agentic-reasoning-llm-reading-guide.md`
- **CIP progress:** See CIP-0002 **Progress Updates** dated 2026-03-27

## Progress Updates

### 2026-03-27

Task created from implementation-session deliberation (paused). Discussion captured in CIP-0002 progress update. Awaiting Stage 3 (design alternatives) and user authorization before code changes.

### 2026-03-28

Status changed from **Proposed** to **Ready**. All design decisions resolved (see CIP-0002 progress update 2026-03-28). Six sub-tasks created under `backlog/features/2026-03-28_*`:

1. `policy-return-shape-and-decide` — foundational (no deps)
2. `reasoning-field-in-payload` — depends on 1
3. `update-heuristic-policies-examples` — depends on 1; parallel with 2, 4
4. `update-data-model-spec` — depends on 1 + 2; parallel with 3
5. `pluggable-llm-policy` — depends on 1 + 2; parallel with 3, 4
6. `update-notebooks-factorization-idk` — depends on 3 + 5

Critical path: 1 → 2 → 5 → 6. Ready for Stage 3 (per-task design alternatives) and implementation.

### 2026-03-28 (implementation)

Sub-task **`2026-03-28_policy-return-shape-and-decide`** completed (Stages 3–5). Policy `choice` contract is live in code, tests, examples, and `docs/data-model-spec.md` §3.1.

### 2026-03-28 (tasks 2–5 completed)

- **Task 2 (`reasoning-field-in-payload`):** Completed with logging level swap — L1 = provenance/accountability, L2 = explanation/reasoning. `RecordWriter` strips `reasoning` below Level 2.
- **Task 3 (`update-heuristic-policies-examples`):** Closed — work absorbed into Task 1.
- **Task 4 (`update-data-model-spec`):** Closed — work absorbed into Tasks 1 and 2.
- **Task 5 (`pluggable-llm-policy`):** Completed with expanded scope. Library-level tool-tracing in `SessionAgent.decide()` via `_TraceCollector` + per-agent `tools` config. LLM policy example with zero dependencies. Hybrid merge of tool traces + policy reasoning.

**5 of 6 sub-tasks complete.** Remaining: **Task 6 (`update-notebooks-factorization-idk`)**. 114 tests pass.

### 2026-03-28 (all sub-tasks completed)

**Task 6 (`update-notebooks-factorization-idk`):** Completed. All three notebooks updated to new `choice` shape. `01_minimal_demo` includes a new abstain example (Step 8). Experiment runners verified. LLM integration section in notebooks deferred to a follow-up (the `examples/llm_policy.py` module is ready for users).

**All 6 of 6 sub-tasks complete.** Full test suite: 115 passed, 3 skipped. The parent task is now **Completed**.

### 2026-03-28 (follow-up: notebook restructuring)

After review, the notebook flow needed revision — the abstain section in `01_minimal_demo` felt bolted on. Deliberation led to a restructuring plan:

- **01_minimal_demo**: Remove abstain section; pure hello-world only.
- **02_push_demo**: Add LLM comparison section after analysis (heuristic vs LLM records).
- **03_gridworld_demo**: Replace agent_3 with an LLM-based policy from the start (4 agents, 4 distinct policies).
- **All LLM policies use actual clients** (OpenAI SDK via env var), not mocks.

Also created the Sorrento talk source (`sorrento-doagent.md` in `cabrerac.github.io`) with updated `_snippets/doagent.md` (current Session API, choice shape, reasoning, tools) and new talk-specific snippets for MAS bridge, policies progression, factorisation/IDK, and conclusions.

**New follow-up task**: `2026-03-28_notebook-restructuring-llm-integration`.
