---
id: "2026-09-24_werewolf-doagent-game"
title: "Implement Werewolf as a DOAgent game"
status: "In Progress"
priority: "High"
created: "2026-09-24"
last_updated: "2026-09-25"
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
The environment plays the night and the day.
A live model game is running on the VM and has not been scored yet.

## Acceptance Criteria

- [x] Night order, day vote, roles, and prompts match the published Werewolf game.
- [x] A player reads a line only from the session, and only when that line names the player.
- [x] No event bus from MARBLE is on the path a player uses to read or send a line.
- [x] The truth file is written while the game runs.
- [x] The curves are rebuilt from the session after the game.
- [x] A test shows a wolf line in the wolves' session view and absent from a villager's view.
- [ ] One live model game writes truth, gap, and cost.

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

### 2026-09-25

A Kimi pair is running on the VM.
The DOAgent game is first.
Its truth file has reached night 2.
All nine players are still alive.
Night 1 and most day-1 votes look like empty model replies.
Night 2 shows a real wolf target, a real guard, and a witch save.
`call_model` does not retry an empty tool response.
The session files appear when that game closes.
The service game has not started.
The Qwen service pilot is scored on CIP-0014 and is not this task.

The night, the day, the sheriff, the badge, and the exile vote are in the environment.
The truth file is rewritten while the game runs.
Entropy uses outcome lines.
Modularity uses exile votes stored on `agent_update`.
`cost.json` is written for a DOAgent run and for a service run.
Tests pass.
The next service run stamps each log line and each model call.
The DOAgent runner now stamps lines the same way.

### 2026-09-24

Task opened after the bus-and-session files were rejected.
Step 3 of CIP-0014 is not started.
The split is recorded.
Environment code owns the rules.
The published prompt files, tool schemas, and model name are loaded as data.
The game line is written on the outcome.
The decision and the level 2 explanation stay on the agent update.
The first code slice is one wolf ask and the visibility test.
