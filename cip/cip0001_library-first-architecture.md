---
author: "Christian Cabrera"
created: "2026-01-23"
id: "0001"
last_updated: "2026-02-20"
status: "In Progress"
compressed: false
related_requirements:
- "0001"
related_cips: []
tags:
- cip
- architecture
- library
title: "Library First Architecture"
---

# CIP-0001: Library First Architecture

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
Define the library-first architecture so DOAgent can be embedded as a dependency, with modular adoption of principles (shared data, decentralisation, openness) and optional system-level conveniences.

## Motivation
The primary product is a library, not a monolithic system. This enables reuse across diverse environments, allows teams to integrate DOAgent into existing stacks, and makes incremental adoption possible.

## Detailed Description
This CIP establishes the architectural boundaries and packaging principles for a library-first design. The library should expose stable APIs for core capabilities while keeping orchestration, deployment, and infrastructure choices optional.

Key design goals:
- **Modular adoption**: users can adopt shared data models, decentralised coordination, and openness independently.
- **Composable API surface**: core primitives are small, explicit, and well documented.
- **Optional system layers**: any runtime, control plane, or services are packaged separately from the library.
- **Minimal assumptions**: no required network topology or storage backend.

## Iteration Deliverable (PoC)
A minimal library package that exposes:
- A core module with a small, stable API surface.
- A simple in-memory shared data model adapter.
- A stub agent adapter that can read/write to the shared model.

## Implementation Plan
1. **Define library boundaries**
   - Identify core modules vs optional system layers.
   - Document what is out of scope for the core.
2. **Design core API surface**
   - Define primitives for shared data, agent adapters, and coordination hooks.
3. **Create minimal library scaffold**
   - Provide package structure and baseline documentation.
4. **Add PoC adapters**
   - In-memory shared data model.
   - Stub agent adapter to validate API usage.
5. **Document modular adoption**
   - Provide examples of enabling only selected principles.

## Backward Compatibility
No backward compatibility impact since this is the initial architecture definition.

## Testing Strategy

### Unit tests
Core API boundaries and adapters. Use stubs/mocks to verify individual components (Session, RecordWriter, RunConfig, topology filtering) in isolation. Fast, deterministic, catch logic errors.

### Integration tests
Full-stack wiring: real env + real policies + Session + shared data. These verify that observation structures flow correctly through Session into policies and produce valid actions, that shared maps accumulate from records, and that topology filtering works end-to-end. **Critical for catching bugs at component seams** — e.g. mismatched payload structures, incorrect field nesting, broken wiring between record creation and record consumption.

Integration tests should assert on **behaviour** (agents move, coverage increases, actions are valid integers, shared maps grow) not just record counts.

### Documentation test
Minimal example runs without optional system layers. Examples in `examples/` serve as living documentation and should be runnable.

## Related Requirements
This CIP addresses the following requirements:
- REQ-0001: Library First Architecture

## Implementation Status
- [x] Define library boundaries and modules
- [x] Specify core API surface
- [x] Create package scaffold
- [x] Implement in-memory shared data adapter
- [x] Implement stub agent adapter
- [x] Add minimal documentation and examples
- [x] Extend library definition (additional methods, records, and modules)

## Progress Updates

### 2026-02-02
Iteration 1 complete. Minimal library scaffold, in-memory shared data, stub agent adapter, example, and tests passed. Iteration 2 planned.

### 2026-02-02
Next iteration may extend the library definition (more methods, more record types). If this introduces an architectural shift, open a new CIP. Next iteration can also redefine what we expose and what is transparent for users.

### 2026-02-21
Session API implemented (backlog: 2026-02-19_session-api). Testing strategy updated to include integration tests that verify full-stack wiring (real env + real policies + Session). Two wiring bugs caught during Session rollout (shared_map cell extraction, _move_towards at origin) demonstrated that unit tests with stubs are insufficient — integration tests at component seams are essential.

### 2026-02-21
Library boundaries document (`library-boundaries.md`) updated to reflect the current API surface:
- §3 rewritten around Session as the user-facing API (table of Session methods and what the library does internally)
- §6 scope updated: Session, MongoSharedData, dedup, topology, adapter contract all in core; SQL/stream adapters deferred
- §12 extensibility corrected: adapters are now extensible via `SharedDataAdapter` Protocol; dedup hash and topology are also extensible
- §13 implications rewritten: Session as wiring layer, RecordWriter orchestrates writes, collection-per-kind storage, dedup transparent
- §14 added: Design Alternatives Considered (adapter extensibility, Session entry point, dedup default, collection-per-kind)
- "Extend library definition" checklist item marked complete

### 2026-02-21
Session-first refactoring of validation examples and library internals:
- **Validation examples** cleaned: removed "user responsibility" comments; added `# doagent:` annotations at Session/agent/env integration points; removed dead `provenance`/`accountability` from agent config metadata (Session handles these via RecordWriter at the appropriate logging level, so user-provided metadata was being injected then immediately stripped).
- **Pre-Session dead code removed**: `build_push_agents()`, `build_grid_agents()`, `_wrap_policy_with_metadata()` in validation agent modules — these created `FunctionAgent` instances bypassing Session. Also removed `FunctionAgent`, `SharedDataAdapter`, `DecisionRequest/Response` imports from agent modules.
- **`AgentMetadata` simplified**: only `explanation` field remains (provenance and accountability are RecordWriter concerns, not user config).
- **Session's `_wrap_policy_with_metadata`** cleaned: only injects `explanation`; provenance/accountability injection removed.
- **`run_gridworld_validation`** updated: now passes topology/visibility/hub_id to Session and uses `session.visible_records()` for topology-filtered record access instead of manual `_collect_shared_map` filtering.
- **Top-level `doagent.__init__`** simplified to Session-era exports: `Session`, `RunConfig`, `InMemorySharedData`, `SimpleRecord`. Pre-Session items (`StubAgent`, `new_record`) remain in `doagent.core` for internal/test use.
- **Feature examples** (`minimal_usage.py`, `model_agnostic_agent.py`) rewritten to use Session API.
- **README** module listing restructured: primary API (Session layer) vs internal helpers.
- All 74 tests pass; gridworld validation example runs correctly (66 rounds, 63.5% coverage, 168 agent_updates, 66 outcomes, 168 traces).

## References
- [Library Boundaries](../docs/library-boundaries.md)
- [Data Model Specification](../docs/data-model-spec.md)
- [Adapter Contract](../docs/adapter-contract.md)
