---
author: "Christian Cabrera"
created: "2026-01-23"
id: "0001"
last_updated: "2026-02-02"
status: "Proposed"
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
- [ ] In Progress - Actively being implemented
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
For the PoC iteration:
- **Unit tests** for core API boundaries and adapters.
- **Integration test**: stub agent writes to and reads from the shared data model.
- **Documentation test**: minimal example runs without optional system layers.

## Related Requirements
This CIP addresses the following requirements:
- REQ-0001: Library First Architecture

## Implementation Status
- [ ] Define library boundaries and modules
- [ ] Specify core API surface
- [ ] Create package scaffold
- [ ] Implement in-memory shared data adapter
- [ ] Implement stub agent adapter
- [ ] Add minimal documentation and examples

## Progress Updates

### 2026-02-02
Iteration 1 complete. Minimal library scaffold, in-memory shared data, stub agent adapter, example, and tests passed.

## References
- None yet
