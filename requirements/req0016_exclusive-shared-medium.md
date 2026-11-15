---
id: "0016"
title: "Shared Store as the Only Medium"
status: "In Progress"
priority: "High"
created: "2026-11-15"
last_updated: "2026-11-15"
related_tenets:
- "data-first-shared-model"
- "decentralised-by-design"
- "provenance-and-accountability"
- "library-first"
stakeholders:
- "agent developers"
- "auditors"
- "multi-agent system researchers"
tags:
- requirements
- data-model
- visibility
- provenance
---

# REQ-0016: Shared Store as the Only Medium

## Description

An agent receives information from the environment and from other agents only as records it is allowed to see.
An agent gives information only by writing records.
Private information is written as its own record and is not readable by an agent it was not addressed to.

Each decision names the records the agent was shown.
The library writes that list, because the library hands the records over.
A statement by the agent about which records it relied on remains a claim until it is checked.

A recorded decision can be repeated with a chosen set of records withheld or added, and with the rest of its input unchanged.
The repeated decision is stored and linked to the original.

REQ-0002 requires a shared model that agents can use.
This requirement requires that the shared model is the only medium.
Direct delivery of observations, and reads that skip the visibility rules, do not meet it.

**Why this matters**: The data-first tenet says the shared model is the interface.
The decentralisation tenet says visibility is a configured choice.
Provenance is only meaningful if a decision names the records it was shown.

**Who benefits**: Agent developers, auditors, and researchers who need to reconstruct who could see what.

## Acceptance Criteria

- [ ] Starting information and later observations exist as records before any agent reads them.
- [ ] An agent cannot read a record that the visibility rules and the record audience withhold from it.
- [ ] Information an agent gives to others exists as a record addressed to those recipients.
- [ ] A decision record lists the ids of the records the agent was shown, and the library writes that list.
- [ ] An agent's own earlier records are available to that agent on later decisions.
- [ ] One decision can be repeated with named records withheld or added, and the repeat is stored and linked to the original decision.
- [ ] Existing environments can keep their current call shape while new and updated environments follow this rule.

## Notes

The rule applies to every environment, not only to the studies in REQ-0017.
Hidden Profile currently receives observations from the game loop and does not read the store.
Werewolf reads the store through an unfiltered call and applies its own filter.
The recommended session loop has the same bypass.
Only the attribution run reads through the call that applies the visibility rules.

A single outcome record that holds every agent's private observation cannot be shown to one agent without exposing the others.
Each private observation needs its own record.

## References

- **Related Tenets**: data-first-shared-model, decentralised-by-design, provenance-and-accountability, library-first
- **Related Requirements**: REQ-0002, REQ-0007, REQ-0008
- **Follow-on**: REQ-0017

## Progress Updates

### 2026-11-15

Requirement drafted from a review of the session loop, the record writer, and the Hidden Profile, Werewolf, and attribution runs.
CIP-0016 holds the design.

### 2026-11-15

CIP-0016 was accepted.
Status moved to In Progress.
No backlog tasks exist yet.

### 2026-11-15

Six CIP-0016 backlog tasks now exist.
None is in progress.
