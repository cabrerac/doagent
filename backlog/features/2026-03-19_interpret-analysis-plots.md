---
id: "2026-03-19_interpret-analysis-plots"
title: "Document how to interpret analysis artefacts"
status: "Completed"
priority: "Medium"
created: "2026-03-19"
last_updated: "2026-03-19"
category: "features"
related_cips:
- "0006"
- "0007"
- "0008"
- "0009"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- analysis
- documentation
---

# Task: Document how to interpret analysis artefacts

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Document how users should read and interpret the analysis outputs produced by DOAgent so results are actionable, not just visual artefacts.

Scope covers:
- Provenance tree (cause-to-effect chain from source records to outcomes)
- Trace graph (state transitions, roles, and dedup convergence)
- Causal attribution chart (productive vs redundant contribution)
- Interpretability artefacts as a "justification bundle" (decision links always; explicit explanations when available)

The output should live in user-facing docs and be linked from the main README analysis section and relevant notebooks.

## Alternatives Considered

- **Alternative A:** Keep interpretation guidance only inside notebooks.
- **Alternative B:** Create one dedicated guide and link to it from README and notebooks.

**Selected:** Alternative B.

**Rationale:** A single source of truth avoids drift while notebooks can keep concise reminders.

## Acceptance Criteria

- [x] A user-facing guide explains how to interpret each analysis output with concrete reading tips.
- [x] README analysis section links to the interpretation guide.
- [x] Relevant notebooks include short pointers to the same interpretation guide.
- [x] Guidance is consistent with current analysis implementation and demo outputs.

## Follow-On Gap Identified

Current interpretability output can be useful even when explicit `explanation` records are absent (e.g. `agent_update` records linked via provenance/trace with `_role` metadata). This task now records a follow-on product gap:

- Improve interpretability tooling so it provides strong value even with decision-link-only data.
- Improve presentation when explicit explanation records are present (clearer, more user-facing rendering than raw JSON dumps).
- Treat interpretability as two levels in docs and UX:
  - Level 1: decision linkage / justification structure.
  - Level 2: decision linkage plus explicit explanations.

This gap should be addressed by a dedicated follow-up backlog item in the analysis/interpretability track.
Primary follow-up owner: `backlog/features/2026-03-19_explanations-storage-doc.md`.

## Implementation Notes

Start with concise "what this chart shows" and "how to read" sections. Avoid deep theory; optimize for practical interpretation of actual generated artefacts.

## Related

- CIP: 0006, 0007, 0008, 0009
- PRs: N/A
- Documentation: README.md, notebooks/*, guides/*

## Progress Updates

### 2026-03-19

Task created from previous session handoff item: "Interpret the results (plots)". This backlog task now tracks the work in VibeSafe artifacts.

### 2026-03-19

Implemented `guides/interpreting-analysis.md`; README Analysis links; `guides/README.md` index row; Step 8 pointers in `notebooks/02_push_demo.ipynb` and `03_gridworld_demo.ipynb`. Marked task Completed.

### 2026-03-19 (interpretability follow-up)

Validated against `output/gridworld_run_20260319_171348_ab044ba3`: interpretability export was present and valid but contained linked `agent_update` records only (no explicit `explanation` records). Updated this task to capture the follow-on need for stronger interpretability tools in both "no explanations present" and "explanations present" cases.
