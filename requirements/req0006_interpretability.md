---
id: "0006"
title: "Interpretability of Agent Decisions"
status: "Proposed"
priority: "High"
created: "2026-01-22"
last_updated: "2026-01-22"
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
- [ ] Decisions include human readable rationales or summaries.
- [ ] Explanations can be generated from shared data without contacting the agent.
- [ ] Interpretability information remains available for auditing.

## Notes (Optional)
The explanation format and storage strategy are defined in CIPs.

## References
- **Related Tenets**: interpretability-and-traceability
- **External Links**: None

## Progress Updates

### 2026-01-22
Requirement drafted.
