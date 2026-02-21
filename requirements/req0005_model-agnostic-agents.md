---
id: "0005"
title: "Model Agnostic Agent Core"
status: "In Progress"
priority: "Medium"
created: "2026-01-22"
last_updated: "2026-02-21"
related_tenets:
- "model-agnostic-core"
stakeholders:
- "agent developers"
- "researchers"
tags:
- requirements
- model-agnostic
---

# REQ-0005: Model Agnostic Agent Core

## Description
Agents must be able to use different decision making engines while interacting through the same core interfaces and data contracts. The system should not assume a specific model type or decision mechanism.

This requirement keeps the framework flexible for diverse agent implementations.

**Why this matters**: It enables innovation and avoids locking the system to a single model family.

**Who benefits**: Agent developers and researchers building varied decision systems.

## Acceptance Criteria
- [x] Agents can integrate different decision engines without changing system contracts.
- [x] Core interfaces do not require model specific inputs or outputs.
- [x] The system remains usable across multiple agent model types.

## Notes (Optional)
Adapter patterns and model integration guides are described in CIPs.

## References
- **Related Tenets**: model-agnostic-core
- **External Links**: None

## Progress Updates

### 2026-01-22
Requirement drafted.

### 2026-02-21
CIP-0005 iteration 1 complete (4/4 items). `DecisionRequest`/`DecisionResponse` payloads, `FunctionAgent`, `StubAgent`, and `SessionAgent` protocol implemented. Session API wraps any callable policy via `PolicyRegistry`. Validation examples demonstrate multiple policy types (random, greedy, noop) through the same interface. `model_agnostic_agent.py` feature example confirms model-agnostic design.
