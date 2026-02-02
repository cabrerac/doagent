---
id: "library-first"
title: "Library First"
status: "Active"
created: "2026-01-22"
last_reviewed: "2026-01-22"
review_frequency: "Weekly"
conflicts_with: []
tags:
- tenet
- doagent
---

# Tenet: Library First

## Tenet

**Description**: DOAgent is a library before it is a system. The core value is reusable, composable APIs that integrate into existing stacks without prescribing deployment, orchestration, or infrastructure choices.

**Quote**: *"Build the library first, let systems emerge from it."*

**Examples**:
- Core primitives are provided as packages with clear interfaces and minimal assumptions.
- Users can embed DOAgent in their own runtimes or orchestration layers.
- Extensions are built via plugins rather than bespoke forks.

**Counter-examples**:
- A hard requirement to run a bundled service or control plane.
- APIs that only work inside a specific runtime.
- Features that assume a single deployment topology.

**Conflicts**:
- Potential conflict with convenience features that favour a monolithic system.
- Resolution: keep system features optional and layered on top of the library core.
