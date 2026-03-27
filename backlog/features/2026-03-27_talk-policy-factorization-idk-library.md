---
id: "2026-03-27_talk-policy-factorization-idk-library"
title: "Library support for policy factorization and IDK (talk + demos)"
status: "Proposed"
priority: "High"
created: "2026-03-27"
last_updated: "2026-03-27"
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
