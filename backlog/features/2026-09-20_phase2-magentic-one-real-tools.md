---
id: "2026-09-20_phase2-magentic-one-real-tools"
title: "Phase 2 Magentic-One on DOAgent with real AutoGen specialists"
status: "Ready"
priority: "High"
created: "2026-09-20"
last_updated: "2026-09-20"
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

- [ ] Five agents on a federated Session. Orchestrator writes task and progress ledgers to the store.
- [ ] Live specialists call AutoGen agents. Offline tests use stand-ins (no Playwright, no API key).
- [ ] W-only / T-only cost uses the same policies without a Session (`direct.py`).
- [ ] Gold modes `accept_last` and `none` are documented in config.
- [ ] Judge system prompt lists this team’s agents.
- [ ] Campaign runner accepts `--team magentic_one` and that config.
- [ ] Optional `magentic-one` extra in `pyproject.toml`.

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
