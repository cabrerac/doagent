---
id: "decentralised-by-design"
title: "Decentralised by Design"
status: "Active"
created: "2026-01-22"
last_reviewed: "2026-01-22"
review_frequency: "Weekly"
conflicts_with:
- "data-first-shared-model"
tags:
- tenet
- doagent
---

# Tenet: Decentralized by Design

## Tenet

**Description**: The system must support a spectrum of control from centralised orchestration to federated and peer to peer topologies. Decentralisation is a first class capability, not an afterthought, and should be configurable without rewriting agents.

**Quote**: *"Topology is a choice, not a constraint."*

**Examples**:
- The same agent can run under a central coordinator or in a peer network.
- Coordination protocols can be swapped without changing agent code.
- Federation rules can restrict visibility or authority across domains.

**Counter-examples**:
- A hard requirement that all agents report to a single orchestrator.
- A design that assumes low latency direct calls between all agents.
- Implementations that cannot run without a specific control plane.

**Conflicts**:
- Potential conflict with a single shared data model creating centralised coupling.
- Resolution: enable sharding and partitioning with configurable routing to reduce central coupling.
