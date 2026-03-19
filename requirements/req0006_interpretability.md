---
id: "0006"
title: "Interpretability of Agent Decisions"
status: "Implemented"
priority: "High"
created: "2026-01-22"
last_updated: "2026-01-28"
related_tenets:
- "interpretability-and-traceability"
stakeholders:
- "end users"
- "auditors"
- "system operators"
tags:
- requirements
- interpretability
---

# REQ-0006: Interpretability of Agent Decisions

## Description
The system must provide interpretable explanations of agent decisions that can be understood without direct access to agent runtimes. Explanations should be derived from the shared data model and remain available for review.

This requirement focuses on understanding: users should be able to grasp why an outcome was produced.

**Why this matters**: Interpretability builds trust and enables review of agent behaviour.

**Who benefits**: End users, auditors, and system operators.

## Acceptance Criteria
- [x] Decisions include human readable rationales or summaries.
- [x] Explanations can be generated from shared data without contacting the agent.
- [x] Interpretability information remains available for auditing.

## Notes (Optional)
The explanation format and storage strategy are defined in CIPs.

## References
- **Related Tenets**: interpretability-and-traceability
- **External Links**: None

## Progress Updates

### 2026-01-22
Requirement drafted.

### 2026-02-21
CIP-0006 iteration 1 complete (4/4 items). `ExplanationPayload`, `ExplanationRecord`, `new_explanation_record` implemented. Explanation is a field inside `agent_update.payload.decision` (produced at logging level >= 1). Explanations are persisted in shared data and accessible without contacting agents. Validation examples produce explanation artefacts.

### 2026-01-28
Analysis demo: provenance_walker.py and causal_attribution.py demonstrate external interpretability from recorded data. Provenance chain answers "why did this state happen?"; causal attribution answers "who contributed what?" from trace edges. No agent internals required.

### 2026-01-28 (CIP-0006 Implemented)
CIP-0006 moved to **Implemented**: `doagent.analysis.interpretability` delivers transition-level atomic explanations from shared data (`build_atomic_explanations`, Level 1/2). **REQ-0006 acceptance criteria are satisfied** for the stated requirement (interpret decisions from shared data without agent access). **Advanced** interpretability products (episode narratives, joint graph+text, Q/A bundles, etc.) are **not** required by this REQ; track as future requirements/CIPs when scoped. See `backlog/features/2026-03-19_explanations-storage-doc.md` (deferred section).
