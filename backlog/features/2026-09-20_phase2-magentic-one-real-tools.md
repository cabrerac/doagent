---
id: "2026-09-20_phase2-magentic-one-real-tools"
title: "Phase 2 Magentic-One on DOAgent with real AutoGen specialists"
status: "In Progress"
priority: "High"
created: "2026-09-20"
last_updated: "2026-09-23"
category: "features"
related_cips:
- "0012"
owner: "Christian Cabrera"
dependencies:
- "2026-09-20_phase1-wt-baselines-cost"
tags:
- backlog
- validation
- evaluation
- attribution
- magentic-one
---

# Task: Phase 2 Magentic-One on DOAgent with real AutoGen specialists

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Build the Phase 2 team from CIP-0012. Five roles match Magentic-One:
orchestrator, WebSurfer, FileSurfer, Coder, ComputerTerminal.

Specialists are Microsoft’s AutoGen agents (`MultimodalWebSurfer`,
`FileSurfer`, `MagenticOneCoderAgent`, `CodeExecutorAgent`), wrapped as
Session policies. The Session store is the mailbox. Do not start
`MagenticOneGroupChat`.

The query is a versioned Who&When / GAIA / AssistantBench item. Gold is
new (planted `accept_last`, or annotated after a natural fail). Published
`mistake_step` values do not transfer.

The W / T / D protocol, campaign runner, and judges stay the same. The
judge roster must come from this team, not from the addition-team names.

## Acceptance Criteria

- [x] Five agents on a federated Session. Task and progress ledgers ride on the assign and accept actions.
- [x] Offline tests use stand-ins (no Playwright, no API key).
- [x] Direct host runs the stand-in policies without a Session. W and T collectors share the step clock.
- [x] Judge system prompt lists the roster stored on `gold.json`.
- [x] Optional `magentic-one` extra in `pyproject.toml`. `on_messages` wrapper is in `specialists.py`.
- [ ] Live specialists are the AutoGen objects (`MultimodalWebSurfer`, `FileSurfer`, `MagenticOneCoderAgent`, `CodeExecutorAgent`).
- [ ] Gold mode `none`, campaign `--team magentic_one`, and that config.

## Implementation Notes

Keep specialist objects alive for the whole run so the browser, files, and
shell keep their state. Use one event loop per run for `on_messages`.

Do not write “correct is …” into level-2 explanations.

Planned paths: `experiments/magentic_one/` (`query.py`, `specialists.py`,
`orchestrator.py`, `host.py`, `direct.py`, `run.py`, `config.yaml`, README),
hooks in `evaluate.py`, `campaign.py`, `attribution_comparison.py`,
`tests/test_magentic_one_team.py`.

## Related

- CIP: [0012](../../cip/cip0012_magentic-one-doa-evaluation.md)
- Depends: [2026-09-20_phase1-wt-baselines-cost](2026-09-20_phase1-wt-baselines-cost.md)

## Progress Updates

### 2026-09-20

Task created after the Phase 2 design was agreed. Implementation starts
in the next doagent session. No code in this task yet.

### 2026-09-22

Stand-in team, direct host, collectors, gold roster, and the `on_messages`
wrapper are in. Status moved to In Progress. Next slice: construct the four
AutoGen specialists and pass them into `run_magentic_team`.

### 2026-09-23

The four specialist classes construct. A live browser smoke wrote gold and packs.
Recorded runs write the session views the judge reads. `--team magentic_one` is wired for the stand-in.
The capital campaign did not favour DOAgent. The crate campaign scored at the ceiling.
Next session starts from a Who&When-shaped scenario.
Whether a fully described dataset execution can be replayed here is still open. Do not code the next plant until that is settled.
