---
id: "model-agnostic-core"
title: "Model Agnostic Core"
status: "Active"
created: "2026-01-22"
last_reviewed: "2026-01-22"
review_frequency: "Weekly"
conflicts_with: []
tags:
- tenet
- doagent
---

# Tenet: Model Agnostic Core

## Tenet

**Description**: The framework should not assume a specific decision engine. Agents may use LLMs, RL policies, symbolic planners, or hybrid systems. The core abstractions focus on data flow, coordination, and accountability.

**Quote**: *"The system coordinates decisions, not how they are made."*

**Examples**:
- An agent adapter can wrap an LLM or a rule engine with the same interface.
- The shared data model does not encode model specific artifacts.
- Orchestration logic treats agents as capability providers, not model types.

**Counter-examples**:
- APIs that only accept chat completion style inputs and outputs.
- Data formats that assume prompt and response fields everywhere.
- Coordination logic that relies on model specific features.

**Conflicts**:
- Potential conflict with deep optimisations for a specific model family.
- Resolution: keep optimisations optional and outside the core contracts.
