---
id: "2026-11-15_hidden-profile-store-calibration"
title: "Calibrate the new links on scripted Hidden Profile"
status: "Ready"
priority: "High"
created: "2026-11-15"
last_updated: "2026-11-15"
category: "features"
related_cips:
- "0017"
owner: "Christian Cabrera"
dependencies:
- "2026-11-15_store-medium-call-sites"
- "2026-11-15_decision-repeat"
tags:
- backlog
- evaluation
- hidden-profile
- calibration
---

# Task: Calibrate the new links on scripted Hidden Profile

## Description

Rerun the scripted Hidden Profile game through the store.
Compare the answers with the exact answers already scored.
Use the decision repeat on the scripted policies, where removing a fact has a known effect.
Do not recompute the information-theoretic scores from CIP-0015.

## Acceptance Criteria

- [ ] All 18 deals run through the store at logging levels 0, 1, and 2.
- [ ] Level 1 and level 2 answer the existing record and link questions.
- [ ] Level 0 has no stored links, and the link questions stay unanswered there.
- [ ] A scripted withholding test matches the known effect of removing a fact.
- [ ] The CIP-0015 bit scores are left as they are.

## Implementation Notes

The exact answers live in the Hidden Profile study package and in `output/hidden_profile_20261030_011812`.
This task checks the new links.
It is not a new information-theoretic campaign.

## Related

- CIP: 0017
- CIP: 0015

## Progress Updates

### 2026-11-15

Task created from the accepted CIP-0017.
Not started.
Blocked by the store call sites and the decision repeat.
