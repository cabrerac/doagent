---
id: "2026-03-19_explanations-storage-doc"
title: "Document interpretability storage, retrieval, and presentation model"
status: "Completed"
priority: "Medium"
created: "2026-03-19"
last_updated: "2026-01-28"
category: "features"
related_cips:
- "0006"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- interpretability
- documentation
---

# Task: Document interpretability storage, retrieval, and presentation model

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Document current interpretability storage/retrieval behaviour in the library and analysis output, then propose and document target structure and presentation guidance where gaps are found.

This iteration focuses on **atomic explanations** and their presentation in both interpretability levels.

Current behaviour to capture:
- `interpretability.build_atomic_explanations(record_id, run_id, ...)` retrieval/build path
- relationship between outcome, agent_update, trace, and optional explanation records
- linkage via provenance (`derived_from`) and trace (`enabled_by_id`)
- output artefact `analysis/interpretability/atomic_explanations_for_last.json`
- explanation payload linkage to decisions (`decision_id`) when present
- behaviour when explicit `explanation` records are absent (decision-link-only interpretability)

Target discussion to include:
- two interpretability levels:
  - Level 1: linked decision/justification structure (no explicit explanations required)
  - Level 2: linked decisions plus explicit explanation records
- better user-facing presentation for both levels (not only raw JSON)
- demonstration updates in current examples so users can see both levels in practice

## Atomic Explanation Unit (Iteration 1 Core)

Define one canonical explanation unit per interpreted transition. This unit is the bridge between machine-readable records and human-readable interpretation.

### Canonical machine representation

Minimum fields (logical schema):

- `run_id`: run identifier.
- `round`: round/step index.
- `agent_id`: acting agent.
- `from_state_id`: source outcome/state id (or `initial_state`).
- `to_state_id`: destination outcome/state id.
- `decision_id`: linked `agent_update` id that enabled/derived the transition.
- `decision_action`: action selected by the agent (when available).
- `rationale_text`: optional natural-language explanation attached by the agent.
- `links`: provenance/trace linkage context (e.g. `derived_from`, `enabled_by_id`, `trace_id`).
- `evidence_refs`: ids of records used to assemble this unit (`outcome`, `trace`, `agent_update`, optional `explanation`).

Optional fields for future enrichment (not required in this iteration):

- `goal`, `observation_summary`, `confidence`, `quality_flags`, `attribution_tags`.

### Human-readable rendering template

Render each unit using a stable sentence form:

- With explicit rationale (Level 2):
  - `System was at state <from_state_id>. Agent <agent_id> made decision <decision_action> because "<rationale_text>". As a result, the system ended at state <to_state_id>.`
- Without explicit rationale (Level 1):
  - `System was at state <from_state_id>. Agent <agent_id> made decision <decision_action>. As a result, the system ended at state <to_state_id>.`

Presentation should always preserve links to underlying record ids so users can drill down from text to source records.

## Level-Aware Presentation (Iteration 1 Deliverable 2)

Define presentation as two views over the same canonical atomic unit, depending on whether explicit rationale text exists.

### Level 1 (decision-link-only interpretability)

Use when no explicit `explanation` record / rationale text is attached.

Required presentation behaviour:

- Show the transition skeleton clearly: `from_state -> decision -> to_state`.
- Label the rationale slot as missing in a neutral way (e.g. "no explicit explanation attached").
- Keep agent, round, action, and record-link metadata visible.
- Avoid implying hidden intent not present in records.
- Always include drill-down references (`decision_id`, related `trace_id`, state ids).

Example rendering:

- `Round 14 | agent_2 | S14 -> move_east -> S15 `

### Level 2 (explicit explanation interpretability)

Use when an explicit rationale is available (e.g. via linked `explanation` record or equivalent decision-attached explanation field).

Required presentation behaviour:

- Render the same transition skeleton as Level 1.
- Render the rationale text as a first-class field/line.
- Preserve exact wording from the source explanation (no silent paraphrase in canonical view).
- Optionally provide a separate "readable paraphrase" view, but keep source text accessible.
- Keep full record-link metadata for auditability.

Example rendering:

- `Round 14 | agent_2 | S14 -> move_east -> S15 | rationale: "I moved east to explore unseen cells near the boundary."`

### Shared UX principles (both levels)

- Deterministic ordering (e.g. by round, then agent, then timestamp/id).
- Clear distinction between:
  - source-grounded facts (state ids, actions, record links),
  - agent-authored rationale text,
  - optional derived summaries.
- One-click navigation from rendered explanation line to raw source records.
- Compatibility with plot interpretation:
  - trace graph edge -> corresponding atomic explanations
  - provenance node/edge chain -> contributing atomic explanations

## Current Retrieval Contract (`build_atomic_explanations`)

Current implementation in `doagent/analysis/interpretability.py`:

- Inputs: `record_id`, `run_id`, optional `output_base`, optional `write_output`.
- Records loaded from resolved run: `outcome`, `trace`, `agent_update`, `explanation`.
- Link resolution used to build atomic units:
  - Follow traces with `payload.to_id == record_id` and `payload.enabled_by_id` (decision id).
  - Use `outcome.provenance.derived_from` as fallback when no trace edge is available.
  - Attach optional explanation linkage via `payload.decision_id == decision_id`.
- De-duplication: by `(decision_id, from_state_id, to_state_id)`.
- Ordering: by `(round, agent_id, decision_id)` with `round=None` last.
- Output file (when `write_output=True`):
  - `output/<run_id>/analysis/interpretability/atomic_explanations_for_last.json`

Storage/shape notes:

- Level 1 (decision-link-only) is valid: units have no `rationale_text`.
- Level 2 units include rationale text from explanation records and/or decision response metadata.
- Empty result is valid for unknown/unlinked `record_id`.

## Iteration Roadmap

### Iteration 1 (current) — Atomic explanations + level-aware presentation

- Define an atomic explanation unit anchored on state transition:
  - `old_state` -> `decision` -> optional natural-language explanation -> `new_state`
- Document canonical machine-friendly structure and human-friendly rendered text.
- Specify how this unit is presented in:
  - Level 1 (decision-link-only interpretability)
  - Level 2 (decision links plus explicit explanations)
- Update current examples/demos to include explicit agent explanations in at least one path so both levels are demonstrable.
- Keep scope to documentation and example demonstration updates; no large schema refactor in this iteration.

### Later iterations — Advanced interpretability artefacts

Document and prioritise richer artefacts as follow-ons, such as narrative summaries, graph+text joint explanation views, Q/A-ready bundles, and other higher-level interpretability products.

## Alternatives Considered

- **Alternative A:** Keep behaviour implicit in code only.
- **Alternative B:** Publish explicit explanation schema + retrieval contract in docs.

**Selected:** Alternative B.

**Rationale:** Improves maintainability and user understanding, reduces ambiguity for future contributors.

## Proposed improvements (forward-looking)

**When explicit explanations are absent (Level 1):**

- Prefer **atomic units + `rendered_text`** over raw record dumps (implemented in `build_atomic_explanations` and demos/notebooks).
- Optional next steps: highlight transitions missing rationale in a summary line; link each unit to trace-graph edge ids in UI tooling.

**When explicit rationale is present (Level 2):**

- Keep **canonical `rationale_text`** and **sentence `rendered_text`** side by side (implemented).
- Optional next steps: HTML/Markdown report artefact; side-by-side with provenance/trace figures; export bundles for LLM Q&A with citation ids.

## Gaps and target direction (schema / storage / presentation)

**Current state:** Rationale for Level 2 can come from `kind="explanation"` records (`decision_id`) and/or **Session metadata**-injected text on the decision response (`agent_update` payload). Atomic JSON is stable for tooling.

**Residual gaps (not blocking Iteration 1):**

- Filename `atomic_explanations_for_last.json` is fixed regardless of `record_id`; a future improvement is `atomic_explanations_for_<record_id>.json` or a single manifest index.
- Multi-outcome runs may want batch export of atomic units for all outcomes in one pass.

**Rationale for incremental change:** Avoid breaking stored runs; evolve export naming and batch APIs behind new functions or optional flags.

## Advanced interpretability artefacts (deferred)

Explicitly **out of scope** for this backlog item; track in a follow-on task or CIP iteration:

- Narrative summaries (episode- or phase-level) built from atomic units.
- Joint graph+text views (click trace edge → atomic explanation).
- Q/A-ready bundles (curated JSON + citation policy for LLMs).
- Counterfactual or heuristic “what-if” layers (clearly labelled as inferred).

## Acceptance Criteria

- [x] Current interpretability record shapes and retrieval logic are documented in user-facing docs.
- [x] Documentation clarifies where interpretability data lives during/after runs.
- [x] Documentation explicitly defines Level 1 vs Level 2 interpretability behaviour.
- [x] Atomic explanation unit is documented (machine representation + human-readable rendering template).
- [x] Current examples include explanation-emitting agent behaviour to demonstrate Level 2 alongside Level 1.
- [x] Proposed improvements are documented for:
  - stronger tooling when explicit explanations are absent
  - clearer presentation when explicit explanations are present
- [x] If gaps exist, a proposed target schema/storage/presentation approach is documented with rationale.
- [x] Advanced interpretability artefacts beyond atomic explanations are listed and deferred to subsequent iterations.
- [x] Links to this doc are added from README analysis section and/or interpretability docs.

## Implementation Notes

Focus first on accurate documentation of existing behaviour before proposing changes. Emphasise that current tooling should already be useful without explicit explanation records, while also improving the UX when explanations are available. Any schema/storage changes discovered should be tracked via follow-up CIP/backlog items.

## Related

- CIP: 0006
- PRs: N/A
- Documentation: doagent/analysis/interpretability.py, README.md, guides/*

## Progress Updates

### 2026-03-19

Task created from previous session handoff item: "How explanations are stored (and how they should be)". This backlog task now tracks the work in VibeSafe artifacts.

Scope clarified: this is the primary backlog task to discuss interpretability gaps observed in real runs (e.g. valid exports with decision links but no explicit `explanation` records), and to define better tools/presentation for both "no explanations present" and "explanations present" cases.

Roadmap updated: this iteration prioritises atomic explanations and level-aware presentation (Level 1 and Level 2), plus example updates to demonstrate both levels. More sophisticated interpretability artefacts are explicitly deferred to later iterations.

Updated examples for level demonstration: **push** and **gridworld** use `metadata.explanation` on agent configs so Session injects rationale into decisions; `examples/gridworld_demo/gridworld_demo_config.yaml` and notebooks include the same pattern. Runs can still produce Level 1 units for transitions without rationale. `examples/README.md` documents push vs gridworld interpretability behaviour.

Added user-facing links to this backlog task from `guides/interpreting-analysis.md` and `README.md` Analysis section, with concrete Level 1/Level 2 atomic explanation examples in the interpretability guide.

Documented the current retrieval contract for `interpretability.build_atomic_explanations` (record kinds loaded, link resolution order, de-duplication, sorting, output path, and valid Level 1/Level 2 outcomes).

Implemented `interpretability.build_atomic_explanations(...)` with level-aware units and human-readable sentence rendering, plus `write_output` support to `analysis/interpretability/atomic_explanations_for_last.json`. Added tests for Level 1 and Level 2 cases and updated README/guide docs accordingly.

Removed legacy `get_explanations_for` in favour of atomic units; local examples and notebooks print the same interpretability summary (levels + `rendered_text` preview).

### 2026-03-19 (docs closure)

Documented proposed improvements, gap/target direction, and deferred advanced artefacts; marked acceptance criteria complete and task **Completed**.
