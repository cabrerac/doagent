---
author: "Christian Cabrera"
created: "2026-09-24"
id: "0014"
last_updated: "2026-09-25"
status: "Accepted"
compressed: false
related_requirements: []
related_cips:
- "0012"
- "0002"
tags:
- cip
- evaluation
- information-theory
- emergence
- multiagentbench
title: "Information Flow on MultiAgentBench (Service vs DOAgent)"
---

# CIP-0014: Information Flow on MultiAgentBench (Service vs DOAgent)

> **Note**: CIPs describe HOW to achieve requirements (WHAT).
> Use `related_requirements` to link to the requirements this CIP implements.

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [x] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

## Summary

This paper compares a service multi-agent system with DOAgent on information flow.
The scenario is MultiAgentBench Werewolf, reproduced as published.
Failure attribution stays in CIP-0012 and is a different paper.

## Motivation

Service calls leave data in flight.
A later reader depends on whatever log was kept beside the call.
That split is the data dichotomy.
DOAgent makes the shared record the interface, so the same decisions can be read again.

The paper has to show what that change does to information in a group.
It does not ask who made a task fail.
CIP-0012 remains the record of the attribution study.

Emergent group behaviour is the object of this study.
Entropy and modularity are measures of that behaviour.
A higher number is not a win by itself.

## Detailed Description

### Paper story

Current multi-agent systems coordinate by services.
That causes the data dichotomy.
DOAgent is the alternative.
The engineering section introduces the library.
The evaluation compares service runs and DOAgent runs by how closely each record recovers the metric curve of its own game.

Information topography (Lawrence, arXiv:2511.06795) is the theory this evaluation heads toward.
The Fisher information metric and the inaccessible game are not results this CIP must produce.
A short discussion may say that a wiped message is a bottleneck and a retained ledger is what an analyst can read after the game.

### Benchmark

The scenario is Werewolf from MultiAgentBench (Zhu et al., ACL 2025).
Reproduce their roles, rules, communication graph, and LLM agents.
MARBLE is their coordination backbone.
The agents are language models, not scripted policies.
Do not replace the model with a hand-written policy.
Do not shorten the game.
Do not drop roles.
Do not invent a two-agent stand-in and call it Werewolf.

Their config names gpt-4o for the village and for the wolves.
Both runs in a pair use one university model instead, through the university proxy.
The scored pilot used Qwen/Qwen3.8-27B-FP8.
The pair that is running uses moonshotai/Kimi-K3.
The village side and the wolf side use that same model.
Published gpt-4o scores are not comparable with these runs.
The substitution is the model name only.
Roles, night order, day vote, and prompts stay theirs.

Their task score for Werewolf is rule-based.
Their coordination score and their counts of emergent patterns come from another model reading the transcript.
Those published scores are context.
This CIP does not try to match their leaderboard.

The patterns they already name are the phenomena to look for.
Those patterns are selective information sharing, trust splitting the group, and roles changing strategy over the game.
This CIP does not invent a new label for who failed.

### Two sets of runs

Play stays private in both systems.
A player reads only messages addressed to that player.
Roles, night order, day vote, and prompts stay as published.
Both systems in a pair use the same model.
The running pair uses moonshotai/Kimi-K3.

Run n service games and n DOAgent games.
The games do not have to be the same nights.
Each game has its own metric curve, whether or not anyone plots it.
Entropy at a phase is how widely each named fact is held.
One holder scores 0.
Every player holding the fact scores 1.
Modularity at a day is computed on the vote graph.
One group that contains every link scores 0.

Each run writes a truth file while it plays.
The truth file records the audiences and the votes at each phase.
Recovery never opens that file.
The service curve is rebuilt from the nine player logs only.
The DOAgent curve is rebuilt from the session only.
A missing name counts as a total miss against the truth point for that phase.

The gap for one game is the mean distance between its truth curve and its recovered curve.
Average those gaps across the n runs.
Report the spread of the n gaps along with the mean.
Average inside each game before averaging across games.
Do not rank the systems by which raw entropy is larger.

The evidence is Werewolf.
The same procedure can be reused on another scenario.
These runs do not by themselves show that the gap would match in every scenario.

Record storage, file count, and tokens for each run.
Record wall time as well.
Wall time may not separate the systems, because both send the same kind of model call.

### What this CIP does not do

Do not continue the log 36 re-execution as the evaluation of this paper.
Do not copy Who&When mistake indexes onto a new trace.
Do not build a new failure dataset.
Do not treat graph entropy as a reproduction of Lawrence's Fisher geometry.

## Implementation Plan

1. **Confirm the published Werewolf setup.**
   - Read the MultiAgentBench roles, rules, graph, and model settings from their paper and code.
   - Record any setting that cannot be matched, and stop rather than substitute a simpler game.

2. **Service runs.**
   - Run their Werewolf agents with message passing only, n times.
   - Keep each player's log.
   - While the game plays, write the truth file of audiences and votes.
   - Rebuild the entropy curve and the modularity curve from the player logs only.

3. **DOAgent runs.**
   - The environment owns the rules: roles, who is alive, night order, and the day vote.
   - Load the published prompt files, tool schemas, and model name as data.
   - Do not import their environment class or their agent class.
   - Run the same roles and rules, n times.
   - Each player reads earlier outcome lines from the session, and only lines whose recipient list names that player.
   - The environment writes that line on the outcome: speaker, recipients, and the text the rules allow.
   - The player writes the decision on the agent update.
   - Logging levels follow the library. Level 0 keeps the outcome and the decision. Level 1 adds the trace, provenance, and accountability. Level 2 also keeps the explanation and the reasoning.
   - At level 2 the player adds one explanation instruction beside the loaded prompt. The published prompt files stay unchanged.
   - The explanation stays on the agent update. It is not copied onto the outcome line.
   - While the game plays, write the same kind of truth file.
   - Rebuild the curves from the session only.
   - The session has to be the record that run wrote, not a copy of the truth file made afterwards.

4. **Gaps and cost.**
   - For each game, average the distance between the truth curve and the recovered curve.
   - Average those game gaps across the n runs, and report the spread.
   - Count a missing recovered point as a total miss.
   - Record storage, file count, tokens, and wall time.

5. **Theory note.**
   - In the paper discussion, relate the player logs and the session to information topography.
   - Leave the Fisher metric for a later study.

## Backward Compatibility

CIP-0012 stays in progress as the attribution paper.
Existing attribution campaigns and the log 36 smoke run stay on disk.
They are not inputs to this evaluation.
Library APIs do not change in this CIP.
The new work lives under the experiments tree.

## Testing Strategy

A reproduction check compares the service run with the published Werewolf setup.
Roles, graph, and rules must match before any DOAgent run counts.
Unit tests cover entropy and modularity on a fixed Night 1 case.
They do not replace a live Werewolf game.
A run counts only when its truth file and its recovery artifact are separate.
The paper reports the mean gap and the spread of gaps for each system.
A discarded game, such as one that breaks their rules, is reported as discarded.

## Related Requirements

No new requirement id is attached yet.
The shared-data claim is CIP-0002.
The attribution study this paper is not doing is CIP-0012.

## Implementation Status

- [x] Separate this paper from the attribution study
- [x] Confirm the published Werewolf setup
- [ ] Service runs with a truth file and log-only recovery
- [ ] DOAgent runs with a truth file and session-only recovery
- [ ] Mean gap and spread of gaps for both sets
- [ ] Discussion note on information topography

### 2026-09-25

The DOAgent environment owns the night, the day, the sheriff, the badge, and the exile vote.
It does not import the MARBLE environment or agent.
Prompts, tool schemas, and the model name are loaded as data.
The truth file is rewritten after every step.
Recovery reads the session records and does not read the truth file to find those points.
Outcome lines feed entropy.
Exile votes on `agent_update` feed modularity.
Both runners write `cost.json` with storage, file count, tokens, and wall time.
Tests cover visibility, the night, the day, the badge, the truth timing, the modularity gap, and the cost file.
The Qwen service pilot has been scored.
No live DOAgent model game has been scored yet.

The Qwen pilot finished on the VM as `game_20260924_210523_Werewolves_win`.
Werewolves won on day 4.
It has no `cost.json` and no per-call times, because that process started before those writers.
MARBLE renamed the game folder at the end, so the gap writer missed `truth.json` on the VM.
`game_directory` follows that renamed folder.
The local score is entropy gap about 0.118 and modularity gap 0.
Exile votes for days 1 to 4 match the truth file.
Modularity is 0 because each day has one voting bloc.
Operators say Qwen/Qwen3.8-27B-FP8 is the slowest model on the proxy.
The pair uses moonshotai/Kimi-K3 on both arms.

On the evening of 2026-09-25 a pair is running on the VM.
`run_werewolf_pair.sh` starts the DOAgent game, then the service game, with `.wvenv/bin/python`.
Each game writes its own log under `experiments/multiagentbench/werewolf_runs/`.
Do not restart that pair.
The DOAgent truth file has reached night 2 with all nine players alive.
Night 1 had no wolf target and no protection.
Day 1 elected no sheriff and exiled nobody.
Most day-1 votes are abstentions.
Night 2 targeted Priscilla, Stephanie was protected, and the deaths list is empty, so the witch saved herself.
Some model calls return in about a minute.
Others return in 0.1 seconds with no tool call, and `call_model` stores an empty action.
The service runner retries those failures.
The DOAgent runner does not.
Session records are flushed when the DOAgent game closes.
Until then, `latest/truth.json` is the progress file.

### 2026-09-24

Entropy, modularity, the truth file, log recovery, model-call retries, and Linux prompt paths are in the service runner.
One service game on the group VM wrote about 8.1G during Night 1 and stopped with no space left on the disk.
That game is discarded.

## References

- Zhu et al., MultiAgentBench, ACL 2025. MARBLE coordinates LLM agents. Werewolf is a conflicting-goal scenario.
- Lawrence, arXiv:2511.06795, November 2025. Formalises information topography. The Fisher metric is future work for this CIP.
- CIP-0012. Failure attribution. A different paper.
- CIP-0002. Shared data model.
