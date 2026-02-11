---
id: "0001"
title: "Library First Architecture"
status: "In Progress"
priority: "High"
created: "2026-01-22"
last_updated: "2026-02-11"
related_tenets:
- "library-first"
stakeholders:
- "agent developers"
- "platform maintainers"
tags:
- requirements
- library
---

# REQ-0001: Library First Architecture

## Description
The project must provide a library that can be embedded in other systems without requiring a bundled service, runtime, or control plane. Users should be able to integrate DOAgent as a dependency and compose it with their own orchestration, storage, and deployment choices.

This requirement focuses on outcomes: the library is the primary product, and system level features are optional layers built on top. It should allow modular adoption of principles so users can opt into shared data models, decentralised coordination, openness, or any combination.

**Why this matters**: A library first approach maximises reusability and adoption across diverse environments.

**Who benefits**: Agent developers, platform teams, and system integrators.

## Acceptance Criteria
- [ ] DOAgent can be integrated as a library dependency in external projects.
- [ ] Core features are exposed through stable, well documented APIs.
- [ ] System level conveniences are optional and do not constrain library use.
- [ ] Users can adopt principles independently (shared data, decentralisation, openness) without mandatory coupling.

## Notes (Optional)
Packaging, API stability, and compatibility policies are defined in CIPs.

## References
- **Related Tenets**: library-first
- **External Links**: None

## Progress Updates

### 2026-01-22
Requirement drafted.

### 2026-01-28
Status updated to In Progress. CIP-0001 (Library First Architecture) is actively being implemented; grid-world validation (CIP-0010) closed.
