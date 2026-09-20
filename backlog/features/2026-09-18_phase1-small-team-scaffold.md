---
id: "2026-09-18_phase1-small-team-scaffold"
title: "Phase 1 small DOAgent team scaffold with planted who/when"
status: "Completed"
priority: "High"
created: "2026-09-18"
last_updated: "2026-09-18"
category: "features"
related_cips:
- "0012"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- validation
- evaluation
- llm-mas
---

# Task: Phase 1 small DOAgent team scaffold with planted who/when

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

CIP-0012 Phase 1 paper-minimum: a small team on **current** Session APIs (about 2–3 agents; federated hub + leaf is enough). One file-backed run writes substrate **D**. Each scored run has a planted \((i^*, t^*)\).

Prefer **deterministic / scripted policies** for the first scaffold so the team does not need an API key. Optional LLM policies later, reusing `examples/llm_policy.py`.

## Acceptance Criteria

- [x] Two or three participants registered; federated topology with an orchestrator hub.
- [x] Loop uses `decision_context` / `record_update` or `decide(..., inputs=...)` so step inputs land on `agent_update`.
- [x] At least one planted decisive error with gold stored next to the run (`run_id`).
- [x] File adapter run is inspectable (`session.inspect`).
- [x] README: team roles, plant rule, fidelity (not Magentic-One).
- [x] No new core library APIs unless a gap CIP is opened first.

## Implementation Notes

Gap audit (2026-09-18): Session already covers this. Federated leaves only see **hub** records — the hub must republish assignments (and specialist results if the leaf needs them). `create_agents(..., payload_type=)` is **one type for all agents**; put view-specific labels in `inputs` / `choice` or use `record_update(..., payload_type=)` per write.

Need a trivial `wrap_env` environment (even a no-op stepper).

Suggested path: `examples/attribution_eval/` (or similar), not core `doagent/`.

## Related

- CIP: [0012](../../cip/cip0012_magentic-one-doa-evaluation.md)

## Progress Updates

### 2026-09-18

Task created (Ready) after CIP-0012 accepted. Gap audit: no library blocker for the scaffold.

Three-agent scaffold added under `examples/attribution_eval/` (orchestrator, solver, checker; recoverability gold on checker).

Paused after the example and `tests/test_attribution_eval.py`. Marked Completed. Next work is `2026-09-18_phase1-wt-judges-lookup`.
