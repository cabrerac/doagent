---
id: "2026-09-24_multiagentbench-werewolf-setup"
title: "Confirm the published MultiAgentBench Werewolf setup"
status: "Completed"
priority: "High"
created: "2026-09-24"
last_updated: "2026-09-25"
category: "features"
related_cips:
- "0014"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- evaluation
- multiagentbench
---

# Task: Confirm the published MultiAgentBench Werewolf setup

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Read the published Werewolf roles, rules, communication graph, and model settings from the MultiAgentBench paper and code.
Record every setting the paired runs must match.
Stop if a setting cannot be matched.
Do not replace it with a shorter game or a scripted policy.

## Acceptance Criteria

- [x] Roles, rules, graph, and model settings are copied from their paper or code, with a source for each.
- [x] Any setting that cannot be matched is written down, and the run is not started.
- [x] The service read path and the DOAgent read path are stated as the only intended difference.

## Recorded setup

Source repo: https://github.com/ulab-uiuc/MARBLE
Paper: https://arxiv.org/abs/2503.01935

Roles, from `marble/configs/test_config/werewolf_config/werewolf_config.yaml`.
Three wolf, three villager, one seer, one witch, one guard.
`randomize_roles` is true.
`use_random_names` is true.
The same nine roles are the default list in `marble/environments/werewolf_env.py`.

Rules, from `werewolf_env.py`.
Night order is guard, then wolves, then seer, then witch.
Wolves have five discussion rounds (`rounds_remaining` starts at 5).
Day 1 elects a sheriff, announces the night death with last words, then speeches and a vote.
Later days announce the night death without last words, then speeches and a vote.
The game ends when every wolf is dead, or every non-wolf is dead.
`cooperation_mode` is `cooperative`.
`use_daily_tasks` is true.
`--rounds` defaults to 10, and each round is one full game, not one day.

Graph.
`werewolf_env.py` does not mention a star, chain, tree, or graph topology.
Players act when an event names them as recipients.
The paper's coordination graphs belong to other scenarios, not to this Werewolf code.

Model.
The yaml sets `gpt-4o` for `villager_config` and for `werewolf_config`.
The scored pilot used `Qwen/Qwen3.8-27B-FP8`.
The running pair uses `moonshotai/Kimi-K3`.
That substitution is in CIP-0014.

Read paths.
The service run keeps their recipient list.
An agent acts only on events that name it, and the prompt reads the public summary plus that agent's own private slot.
The DOAgent run keeps the same roles, order, and prompts.
Each decision is written to the session, and the next agent reads that record.

Cannot match as published.
`scripts/werewolf/run_simulation.sh` is truncated in the repository and is not a valid command.
The code default `--config_path` points at `werewolf_config_4o.yaml`, which is not in the repository tree.
The yaml the readme names, and the one recorded above, is the file to load.
One service game has been scored.
The gap is recorded on CIP-0014.

## Implementation Notes

The agents are language models coordinated by MARBLE.
The service run shows an agent only the messages it is sent.
The DOAgent run writes each decision to a session and later agents read that record.
Entropy and modularity come after both runs exist.
This task does not implement those measures.

## Related

- CIP: 0014

## Progress Updates

### 2026-09-25

The Qwen service pilot is scored on CIP-0014.
The running pair uses moonshotai/Kimi-K3.

### 2026-09-24

Task created after CIP-0014 was accepted.
The published config names gpt-4o.
Both runs will use Qwen/Qwen3.8-27B-FP8 instead, and that is recorded in CIP-0014.
The published launch script is truncated.
Werewolf has no coordination graph in code.
The settings are recorded above.
A service game was started later.
The DOAgent files added the same day still call MARBLE's bus.
They do not implement the DOAgent read path described above.
