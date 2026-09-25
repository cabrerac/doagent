---
id: "2026-09-24_werewolf-doagent-game"
title: "Implement Werewolf as a DOAgent game"
status: "In Progress"
priority: "High"
created: "2026-09-24"
last_updated: "2026-09-24"
category: "features"
related_cips:
- "0014"
owner: "Christian Cabrera"
dependencies:
- "2026-09-24_multiagentbench-werewolf-setup"
tags:
- backlog
- evaluation
- multiagentbench
---

# Task: Implement Werewolf as a DOAgent game

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Write the published Werewolf game the way the gridworld example is written.
The environment owns the turns, the roles, and who is alive.
Each agent reads earlier lines from the session and writes its action back to the session.
The published prompt files, tool schemas, and model name are loaded as data.
Do not import their environment class or their agent class.

`run_werewolf_doagent.py`, `werewolf_doagent.py`, `werewolf_session.py`, and `werewolf_player.py` are the DOAgent side.
The first slice asks the living wolves for one target and records that line on the outcome.

## Acceptance Criteria

- [ ] Night order, day vote, roles, and prompts match the published Werewolf game.
- [ ] A player reads a line only from the session, and only when that line names the player.
- [ ] No event bus from MARBLE is on the path a player uses to read or send a line.
- [ ] The truth file is written while the game runs.
- [ ] The curves are rebuilt from the session after the game.
- [x] A test shows a wolf line in the wolves' session view and absent from a villager's view.

## Implementation Notes

The service runner stays the service side of CIP-0014.
This task is only the DOAgent side.
The environment code owns roles, who is alive, night order, and the day vote.
Prompt text, tool schemas, and the model name come from the published files.
Those files are data.
The DOAgent game does not import their environment class or their agent class.
The environment writes each game line on the outcome.
The player writes the decision on the agent update.
Logging level 2 keeps an explanation on that agent update.
The player adds the explanation instruction itself.
The published prompt files stay unchanged.

## Related

- CIP: 0014

## Progress Updates

### 2026-09-24

Task opened after the bus-and-session files were rejected.
Step 3 of CIP-0014 is not started.
The split is recorded.
Environment code owns the rules.
The published prompt files, tool schemas, and model name are loaded as data.
The game line is written on the outcome.
The decision and the level 2 explanation stay on the agent update.
The first code slice is one wolf ask and the visibility test.
