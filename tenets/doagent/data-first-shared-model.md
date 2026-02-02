---
id: "data-first-shared-model"
title: "Data First Shared Model"
status: "Active"
created: "2026-01-22"
last_reviewed: "2026-01-22"
review_frequency: "Weekly"
conflicts_with:
- "decentralised-by-design"
tags:
- tenet
- doagent
---

# Tenet: Data First Shared Model

## Tenet

**Description**: The shared data model is the primary interface between agents. Agents communicate by reading and writing structured data in a shared substrate (file, database, stream, or object store). This makes agent state observable, queryable, and auditable without relying on implicit message chains.

**Quote**: *"Make data the interface, and multiagent architectures become inspectable."*

**Examples**:
- Agents post decisions and intermediate artifacts into a shared event stream.
- State transitions are recorded as updates to a shared model with clear schemas.
- External tools can query agent state without connecting to agent runtimes.

**Counter-examples**:
- Agents only pass opaque chat messages between themselves.
- Agent logic depends on in-memory state that is not recorded externally.
- Coordination requires direct RPC between agents with no shared data trail.

**Conflicts**:
- Potential conflict with decentralisation when a single shared model becomes a bottleneck.
- Resolution: support sharding and partitioning strategies, and make them configurable by the library user.
