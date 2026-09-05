---
author: "Christian Cabrera"
created: "2026-02-03"
id: "0004"
last_updated: "2026-09-05"
status: "Implemented"
compressed: false
related_requirements:
- "0004"
related_cips:
- "0003"
tags:
- cip
- participation
- architecture
title: "Open Participation Registry"
---

# CIP-0004: Open Participation Registry

> **Note**: CIPs describe HOW to achieve requirements (WHAT).
> Use `related_requirements` to link to the requirements this CIP implements.

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [ ] In Progress - Actively being implemented
- [x] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

**Implemented** means the PoC plus inspectable participation events and topology-filtered membership at decision
time (`visible_participants`, federated hub roster). **REQ-0004** acceptance criteria are all met. Replay of the live
registry after restart, admission policy, and cross-domain discovery remain future iterations — they do not block
this status.

## Summary
Define participation records and a registry interface so agents can join, leave, and advertise capabilities in an open system.

## Motivation
Open participation requires discoverable capabilities and stable interfaces so agents can integrate without bespoke wiring. A minimal registry provides a shared contract.

**Alignment with DOA and the agentic reasoning paper.** The paper states that multi-agent evolution requires **shared memory, communication mechanisms, and collaboration** — the three DOA principles. Openness (open collaboration) is the **collaboration** pillar: who can join, what they can contribute, and how participation scales. The registry and participation model enable the kind of multi-agent collaboration the paper has in mind (agents joining, leaving, advertising capabilities) without bespoke wiring, so that the shared data model and topology (the other two pillars) can operate in an open ecosystem. See `papers/agentic-reasoning-llm-reading-guide.md` §3 for the full mapping.

## Detailed Description
Iteration 1 focuses on participation records and an in-memory registry.

Options considered:
- **Option A**: Central registry interface with in-memory implementation.
- **Option B**: Decentralised registry with gossip or peer-to-peer discovery.
- **Option C**: Hybrid registry with pluggable backends.

We select **Option A** for the PoC. It provides a simple contract while deferring decentralised discovery to later iterations.

Key points:
- ParticipationRecord captures agent id, capabilities, resource limits, and optional metadata.
- ParticipationRegistry interface defines register, update, deregister, get, and list methods.
- InMemoryParticipationRegistry provides a minimal adapter.
- **The participation registry must be exposed** so that examples and run loops can use it when agents join or leave. Today the registry exists in the library but is not wired to the Session: users cannot pass a registry in config or obtain one from the session, so scenarios that simulate or implement join/leave (e.g. energy-based leave/rejoin) cannot register or deregister agents with the library. Exposing the registry (e.g. via Session config and a session property or accessor) is required so that openness is usable in examples and in production run loops.

### Discussion items / Future iteration

- **Registry vs store / chunk ownership.** Today the registry (who is in, capabilities) is separate from the shared data store. If the shared data model becomes distributed (CIP-0002/0003: chunks per agent or group), the registry may need to describe **data placement** or **chunk ownership** (e.g. "agent X hosts chunk for kind K in region R"). So "align participation registry with topology" can evolve into "registry describes who holds which chunk." For future iteration.

- **Admission and policy enforcement.** Already in gaps. "Who can join" may depend on policy (e.g. only agents that accept a given contract); admission and policy hooks keep openness manageable at scale. No change to scope; ensure it remains an explicit discussion topic.

- **Discovery across domains.** Open collaboration across organisations may require **discovery** beyond a single registry: (a) **participant discovery** — finding agents or capabilities across multiple registries or domains (e.g. federated directory, registry-of-registries); (b) **data/resource discovery** — finding where a given chunk or capability lives when data is distributed. For future iteration.

- **Persistence of participation.** Writing `participation` events through the shared-data adapter (file / Mongo)
  persists the **event log**. The live registry (who is in right now) stays in-memory for the run. A later iteration
  may **replay** those events into the registry after a restart so live membership survives process restart too.

- **Federated roster is a default protocol, not a membership invariant.** Join/leave/update records name one actor. The hub `roster` snapshot (`payload.members`) is how the *current* federated coordination protocol republishes membership so leaf agents can see it under the hub-only visibility filter. Other relay or visibility choices (for example the hub re-emitting each join/leave with `actor=hub`) belong on CIP-0003 as replaceable coordination protocols, not as extra CIP-0004 record kinds.

## Iteration Deliverable (PoC)
- Participation record structure.
- Registry interface + in-memory implementation.
- **Expose the participation registry** so callers can use it (e.g. via Session: accept an optional registry in config and expose it on the session, or provide a session method to obtain the registry). Without this, examples cannot register/deregister agents when they join or leave.
- Example and tests for participation registration and retrieval (using the exposed registry).

## Implementation Plan
1. **Define participation record**
   - Capture agent id, capabilities, and resource limits.
2. **Define registry interface**
   - Register, update, deregister, get, list operations.
3. **Implement in-memory registry**
   - Simple adapter for tests and examples.
4. **Expose the participation registry through the session**
   - Allow Session to accept an optional participation registry (e.g. in config or constructor) and expose it (e.g. `session.participation_registry` or `session.get_participation_registry()`). Default: none or an in-memory instance created by the session when participation is enabled. This enables examples and run loops to call register/deregister when agents join or leave.
5. **Update examples and tests**
   - Cover registration and listing using the exposed registry.
6. **Write participation into the shared data model** (blocking item; backlog
   `2026-09-05_participation-into-shared-data`)
   - Dual-write: registry index plus `SimpleRecord` kind `participation` (`join` / `leave` / `update`).
   - Inspectable via `session.inspect("participation")`. Event log persists with the adapter; live index is per-run.

## Backward Compatibility
Additive only; no breaking changes.

## Testing Strategy
- Unit tests for registry operations and record storage.
- Example showing registration and lookup.

## Related Requirements
This CIP addresses the following requirements:
- REQ-0004: Open Participation and Resource Exchange

## Implementation Status
- [x] Define participation record
- [x] Define registry interface
- [x] Implement in-memory registry
- [x] **Expose participation registry through Session** — Session accepts `participation: True` or `participation_registry` in config and exposes `session.participation_registry`; examples and notebooks use it on leave/rejoin (2026-03-17).
- [x] Update examples and tests (gridworld demo and notebook use registry; push notebook notes openness).
- [x] **Write participation into the shared data model** so capabilities and resource limits are inspectable like any other record — dual-write `join`/`leave` events (`RecordWriter.on_participation`); tests cover inspect, file persist, and logging levels (2026-09-05, backlog `2026-09-05_participation-into-shared-data`).
- [x] **Membership at decision time** — `visible_participants(agent_id)` uses the same topology filter as other records; federated hub writes `roster` events (2026-09-05, backlog `2026-09-05_visible-participants`).
- [ ] **Replay participation** into the live registry after restart — future iteration; the event log itself already persists with the adapter (see Discussion items).
- [ ] Registry vs store / chunk ownership (placement in registry when data is distributed) — future iteration; see Discussion items
- [ ] Admission and policy enforcement hooks — future iteration; already in gaps
- [ ] Discovery across domains (participant and data/resource discovery) — future iteration; see Discussion items

## Progress Updates

### 2026-09-05 (coordination protocol pointer)

Federated `roster` / `payload.members` is the **default** relay so leaves can see membership. It is not the only
legal shape. Configurable coordination protocols (visibility + relay) are a CIP-0003 future iteration.

### 2026-09-05 (visible participants)

Agents read who is in from the shared store under the same topology filter. `visible_participants` replays visible
join/leave (and hub `roster` in federated mode). Gridworld passes `participants` into `decide`. CIP stays
**Implemented**; this is a follow-on iteration, not a reopen.

### 2026-09-05 (later)

Blocking item done. `register_participant` / `deregister_participant` append `participation` records; file adapter
writes `participation.jsonl`. Tests passed. CIP and REQ-0004 marked **Implemented**. Closed waits on verification.
Replay of live membership after restart stays a future iteration.

### 2026-09-05

Approach **A** agreed for the blocking item: keep the in-memory registry as a per-run index, and append
`participation` events (`join` / `leave` / `update`) through the shared-data adapter so they are inspectable and
persist with file or Mongo. Live membership after restart (replay) stays a later iteration. Backlog task
`2026-09-05_participation-into-shared-data` created. Spec updated in `docs/data-model-spec.md`. CIP stays
**In Progress** until tests pass.

### 2026-07-28
Reviewed alongside CIP-0007/0008/0009 (all three promoted to **Implemented**). This CIP **stays In Progress**, and the
review pinned down why in code rather than by checklist: `Session.register_participant()` builds a
`ParticipationRecord` with `capabilities` and `resource_limits` and then calls `registry.register(record)` only. The
registry is in-memory and sits outside the shared data model, so participation is never written as a record and cannot
be inspected. `test_participation_registry` passes, but it exercises the registry contract, not transparency.
Recorded as the blocking item in the Status note and Implementation Status above.

### 2026-02-03
Iteration 1 complete. Participation record, registry interface, in-memory registry, and tests added. Tests passed. Iteration 2 planned.

The system now exposes a participation registry contract, but decentralised discovery and policy controls are deferred.

### (later)
The participation registry is not yet exposed through the Session: users cannot pass it in config or obtain it from the session. Scenarios that simulate join/leave (e.g. gridworld energy model) therefore cannot register/deregister agents with the library. This CIP is updated to require **exposing the participation registry** (e.g. via Session config and a session property or accessor) so that examples and run loops can use it.

Gaps and follow-on needs:
- **Expose participation registry through Session** (see Implementation Plan and Implementation Status).
- Align participation registry with topology modes (centralised vs federated).
- Provide distributed or pluggable registry backends.
- Add admission and policy enforcement hooks.

### 2026-02-06
Iteration 2 discussion item: The current simple_push validation example does not demonstrate open participation. Iteration 2 should include a scenario that exercises join/leave and capability discovery.

### 2026-03-13
Added **alignment with DOA and the agentic reasoning paper** to Motivation: openness as the "collaboration" pillar in the paper's triad (shared memory, communication mechanisms, collaboration); registry and participation enable multi-agent collaboration in an open ecosystem. References reading guide §3.

### 2026-03-13
Added **Discussion items / Future iteration**: (1) Registry vs store / chunk ownership — registry may describe data placement or chunk ownership when shared data is distributed. (2) Admission and policy enforcement — keep as explicit discussion topic (already in gaps). (3) Discovery across domains — participant discovery across registries (federated directory) and data/resource discovery (where is chunk X). Implementation Status updated with unchecked items for these.

### 2026-03-19
Clarified **Status** note: **In Progress** is compatible with a long-running openness roadmap; **Implemented** (when reached) still allows further CIP/backlog iterations.

### 2026-03-17
Participation registry exposed through Session: config keys `participation: True` (creates in-memory registry) and `participation_registry` (user-supplied); property `session.participation_registry`. Gridworld example and notebook updated to register/deregister on leave/rejoin; push notebook notes that openness is demonstrated in gridworld. **Persistence:** For future iteration we may persist participation to file or Mongo depending on the shared data model in use; currently the registry is in-memory only. Added Discussion item "Persistence of participation" and Implementation Status item for persist participation (file/Mongo).

## References
- Backlog: `backlog/features/2026-09-05_participation-into-shared-data.md`
- Spec: `docs/data-model-spec.md` §3.3
