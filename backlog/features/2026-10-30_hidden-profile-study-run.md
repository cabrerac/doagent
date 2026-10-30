---
id: "2026-10-30_hidden-profile-study-run"
title: "Run the Hidden Profile study into one timestamped folder"
status: "Completed"
priority: "Medium"
created: "2026-10-30"
last_updated: "2026-10-30"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies:
- "2026-10-15_hidden-profile-doagent-implementation"
- "2026-10-15_hidden-profile-marble-implementation"
- "2026-10-07_controlled-observability-campaign"
tags:
- backlog
- experiment
- hidden-profile
---

# Task: Run the Hidden Profile study into one timestamped folder

## Description

Play all 18 Hidden Profile deals once.
Write that run under `output/`, with a timestamp in the folder name.
Score the saved files, then draw the figures from those tables.
The rules, the parsers, and the bit measures stay where they are.

## Acceptance Criteria

- [x] One command writes `output/hidden_profile_YYYYMMDD_HHMMSS`.
- [x] Each deal folder holds session levels 0, 1, and 2 and the MARBLE logs.
- [x] The score, the question grid, the dimension summary, and the bit charts come from those files.
- [x] A later run writes a new folder and leaves the earlier run in place.
- [x] The single-deal commands stay available for one episode.

## Implementation Notes

The current figures sit in `output/hidden_profile/`.
That folder has no timestamp, and git ignores `output/`.
`score.py`, `curves.py`, and `breakdown.py` each walk the deals separately.
Session level 1 is stored as `doagent` by the score and as `D1` by the curves.
The question figures read only `D0`, `D1`, and `D2`.

## Related

- CIP: 0015

## Progress Updates

### 2026-10-30

Task created after checkpoint 4.
The pilot result is already scored.
This task is the one command that reproduces it.
It has not been started.
The command is `python -m experiments.runners.hidden_profile_study`.
The scored folder is output/hidden_profile_20261030_011812.
It holds all 18 deals, the score, the figures, and campaign.json.
A second run with the same stamp is refused.
The single-deal commands are still in place.
