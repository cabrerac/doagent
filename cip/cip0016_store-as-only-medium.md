---
author: "Christian Cabrera"
created: "2026-11-15"
id: "0016"
last_updated: "2026-11-15"
status: "In Progress"
compressed: false
related_requirements:
- "0016"
- "0002"
- "0007"
- "0008"
related_cips:
- "0002"
- "0015"
- "0017"
tags:
- cip
- shared-data
- visibility
- provenance
- decisions
title: "Shared Store as the Only Medium"
---

# CIP-0016: Shared Store as the Only Medium

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [x] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented
- [ ] Deferred - Postponed

## Summary

This CIP makes the shared store the only medium between the environment, the agents, and later decisions.
An agent is shown only records it is allowed to see.
Anything it tells others is a record.
The library writes, on each decision, the ids of the records that were shown.
A decision can be repeated with named records withheld or added.

The change is a library contract.
Every environment is expected to follow it, including environments that are not part of CIP-0017.
CIP-0017 is the evaluation that needs the contract.
This CIP does not define that evaluation.

**Which requirements does this CIP address?** REQ-0016, with REQ-0002, REQ-0007, and REQ-0008.

## Motivation

REQ-0002 is implemented, and agents can coordinate through records.
Several current paths still move information around the store.

Hidden Profile passes observations from the game loop straight into each decision.
Those agents never read the store.
Werewolf does read stored outcomes, but through the unfiltered inspect call, and the experiment applies its own filter.
The visibility rules are skipped.
The recommended loop in the session documentation has the same shape.
Passing an observation in, then writing the decision, does not record which earlier records the agent was shown.
The decision writer currently stores an empty source list.

One outcome record also holds every agent's private observation.
That record cannot be shown to one agent without exposing the others.

Until these paths go through the store, a link question is answered from text that happens to have been copied, not from a link the library recorded.
CIP-0015 left the library unchanged on purpose.
That limit is what this CIP removes.

## Detailed Description

### Rule

An agent receives only records it is allowed to see.
An agent gives information only by writing records.
The environment writes each private observation as a record addressed to one agent.
Messages between agents are records addressed to their recipients.

### Who writes which link

The record envelope already has a derived_from list.
Decisions write it empty.

Two different facts must not be mixed.

Shown means the records the library handed to the agent for that decision.
The library writes this list.
If the agent wrote it, the list would be a self-report, and a service log could claim the same thing.

Used means the records the agent says it relied on.
Only the agent can say that.
The statement stays a claim until a repeat of the decision tests it.
This CIP stores the claim when the agent provides it.
The repeat itself is also in this CIP.
The interpretation of the repeat for a study belongs to CIP-0017.

### What changes in the library

Reset currently writes nothing, so starting private information never becomes a record.
The environment writes each private item as its own record before the first decision.

Step currently writes one outcome record that contains every agent's observation.
It will write one record per agent, addressed to that agent.

Visibility currently depends only on who wrote a record.
A record may also carry an audience.
The filter keeps a record when the reader is allowed to see the author and is in the audience.
An empty audience means every agent who may see that author.

Decide currently records whatever the caller passes in, and the source list is empty.
The default input becomes the records the agent is allowed to see.
The library writes their ids into derived_from.
A caller may still pass an explicit input, so existing experiments keep running while they are moved over.

A decision record currently holds the inputs and the reasoning together.
Another agent cannot read the decision without also reading that private material.
The decision stays private to the acting agent.
Anything other agents should see is a separate message record, addressed to those recipients.

Agent memory that lives outside the store cannot be reconstructed.
Memory that later decisions depend on is written as records addressed to that agent.
A later decision is then rebuilt from the store.

There is no way to repeat one decision.
The library will call the same policy again with a stated set of records withheld or added, repeat the call a stated number of times, and store each repeat as a record linked to the original decision.

### What stays outside the core

Full prompt traces are captured where the model is called.
They are an experiment export.
They must not contain record ids, so the trace reading cannot peek at the store's links.

Helpers that walk links, or that list who was shown a record, start in the experiment layer.
They become library API only after CIP-0017 has used them.

Storing ids instead of copies should shrink decision records.
CIP-0015 recorded 77,012 bytes for a session file against 1,831 bytes for the component logs.
The new size is measured, not assumed.

### What does not change

The record envelope keeps its current fields.
Provenance and accountability stay optional and still follow the logging level.
The three topologies stay as they are.
Audience is an additional filter, not a fourth topology.
Logging levels still decide whether provenance is written.
A run at level 0 has no derived_from list, and link questions on that run stay unanswered.
That is the same level split CIP-0015 already reports.

### Alternatives considered

Leave observations on the call path and only ask agents to copy ids into their JSON.
Rejected.
The agent would be reporting what it was shown, and the library would not know.
The Hidden Profile flaw would remain, because those agents never read the store.

Give every agent the one combined outcome record and rely on the policy to ignore other agents' fields.
Rejected.
The private fields would be in a record the agent is allowed to read.

Treat a repeated decision as an experiment script with no library support.
Rejected for the long term, because every environment would reimplement it.
The first version can still live beside the session and move into the library once the call shape is stable.
The contract, the stored link to the original decision, and the fixed rest of the input belong to this CIP either way.

## Implementation Plan

1. Add an optional audience on records and apply it inside the visibility filter.
2. Write one addressed record per private observation on reset and on step.
3. Keep the combined outcome available for existing readers until those readers move.
4. Split a decision from the message records other agents may read.
5. Make the default decision input the visible records, and write their ids into derived_from.
6. Keep the explicit input argument as an override.
7. Repeat one decision with a withheld or added set, and store the repeats linked to the original.
8. Move Hidden Profile onto the store and cover it with the existing question checks.
9. Move the Werewolf read onto the visibility call.
10. Update the session documentation so the recommended loop reads from the store.

## Backward Compatibility

Callers that pass an explicit input keep their current behaviour.
The default changes for callers that do not.
Existing session files keep their kinds and envelope fields.
New observation records are added.
They do not replace the combined outcome until the readers of that outcome have moved.
A level 0 run still omits provenance.

## Testing Strategy

Tests cover the audience filter for centralised, peer-to-peer, and federated topologies.
Tests check that a private observation record is visible to the addressed agent and hidden from the others.
Tests check that a decision written without an explicit input lists the ids it was shown.
Tests check that an explicit input still overrides that default.
Tests check that a repeat with one record withheld keeps every other input and links to the original decision.
The current Hidden Profile question checks are run again after that game reads the store.
The existing session tests stay green for callers that pass inputs.

## Related Requirements

- REQ-0016, the shared store is the only medium.
- REQ-0002, the shared model is the agent interface.
- REQ-0007, decision chains are traceable.
- REQ-0008, provenance names the inputs of a record.

## Backlog Tasks

- [Add an audience to records and apply it in the visibility filter](../backlog/features/2026-11-15_record-audience.md)
- [Write one addressed record per private observation](../backlog/features/2026-11-15_addressed-observations.md)
- [Separate private decision records from message records](../backlog/features/2026-11-15_decision-message-split.md)
- [Take the default decision input from the store and record what was shown](../backlog/features/2026-11-15_decision-shown-links.md)
- [Repeat one decision with records withheld or added](../backlog/features/2026-11-15_decision-repeat.md)
- [Move Hidden Profile, Werewolf, and the session loop onto the store](../backlog/features/2026-11-15_store-medium-call-sites.md)

## Implementation Status

- [x] Audience on records and in the visibility filter
- [x] One addressed record per private observation
- [x] Decision records separated from message records
- [x] Default decision input taken from the store
- [x] Shown ids written by the library
- [x] Decision repeat with records withheld or added
- [x] Hidden Profile moved onto the store
- [x] Werewolf read moved onto the visibility call
- [x] Session documentation updated

## References

- `doagent/core/session.py`, decide, visible_records, decision_context, and the recommended loop.
- `doagent/core/_internal/record_writer.py`, the empty source list on agent decisions.
- `doagent/records/record.py`, derived_from on provenance.
- `experiments/information_flow/hidden_profile/run_doagent.py`, observations passed in from the loop.
- `experiments/multiagentbench/run_werewolf_doagent.py`, outcomes read through inspect.
- CIP-0015, the study that left the library unchanged.
- CIP-0017, the evaluation that depends on this contract.

## Progress Updates

### 2026-11-15

CIP drafted.
Status is Proposed.
No code changes are authorised by this document alone.

### 2026-11-15

Status moved to Accepted.
Backlog tasks are not created yet.

### 2026-11-15

Six backlog tasks were added.
The audience filter is the first task.
No task is in progress.

### 2026-11-15

Status moved to In Progress.
The audience task is complete.
The audience is one new field on the record envelope, empty by default, and every existing field is kept.
It is not stored inside accountability, because that block is dropped at logging level 0.
Three rules were settled during implementation.
The author of a record always reads it.
The federated hub must be named in an audience like any other agent.
An audience never shows a record to an agent that may not read its author.

Peer-to-peer and federated topologies stay as they are.
An agent reads the environment only through an author it can already see, a peer or the hub.
An observation written by the environment stays hidden from an agent that cannot see that author.
The audience does not open that path.

### 2026-11-15

Reset and step each write one observation record per agent.
The environment is the author and the audience is that agent.
The payload holds the round and that agent's observation.
Reset uses round 0.
The combined outcome is still written.
A reset that does not return a dict of observations writes none of these records.
The records are written at every logging level.

### 2026-11-16

A decision record is addressed to the acting agent.
A response that carries a message stores a separate message record.
That message drops the reasoning and the full input.
Call decide with no observation and no inputs to read the records the agent may see.
The library writes those ids into the decision provenance.
An observation or an inputs argument still overrides that default.
Logging level 0 writes no provenance.
In a federated setup a leaf also sees the decisions and messages it wrote.
It still learns who is present from the hub.
The addition team publishes the assignment as a message, because the orchestrator is the hub and the decision itself is private.

### 2026-11-16

A decision can be repeated with records withheld or added.
The original input and the changed input run the same number of times.
Each repeat is stored and points at the original decision.
The rest of the run is not replayed.
Hidden Profile decisions read the store.
Each agent can see the environment, and the audience still hides the other agents' observations.
The combined outcome stays in the store for existing readers and is addressed to the environment, so agents are not shown it.
Werewolf players read lines from the observation records the visibility rules allow.
The session example reads from the store.
