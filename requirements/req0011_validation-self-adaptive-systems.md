---
id: "0011"
title: "Validation on Self-Adaptive Systems"
status: "Proposed"
priority: "Medium"
created: "2026-01-23"
last_updated: "2026-01-23"
related_tenets:
- "library-first"
- "decentralised-by-design"
stakeholders:
- "system operators"
- "researchers"
tags:
- requirements
- validation
- self-adaptive
---

# REQ-0011: Validation on Self-Adaptive Systems

## Description
The library must be validated on self-adaptive system scenarios where agents monitor, decide, and reconfigure behaviour at runtime. The validation should show that DOAgent supports decentralised control and modular adoption of principles in adaptive environments.

This requirement focuses on outcomes: representative self-adaptive use cases are implemented and documented with evidence of adaptive behaviour.

**Why this matters**: Self-adaptive systems are a core application area for decentralised multi-agent coordination.

**Who benefits**: System operators and researchers.

## Acceptance Criteria
- [ ] At least one representative self-adaptive use case is implemented.
- [ ] Adaptive behaviour is demonstrated and documented.
- [ ] Decentralised coordination can be configured for the use case.

## Notes (Optional)
Specific adaptive scenarios and evaluation metrics are selected in CIPs. The library is **generic** and usable in self-adaptive (and other) use cases beyond the validation examples we implement; see [Validation and Benchmarks](../docs/validation-and-benchmarks.md) for the principle and for the mapping from the agentic reasoning paper’s §6/§7 to our validation requirements.

## References
- **Related Tenets**: library-first, decentralised-by-design
- **Validation and benchmarks**: [docs/validation-and-benchmarks.md](../docs/validation-and-benchmarks.md) — library genericity; paper §6/§7 as reference for benchmarks and application domains.
- **External Links**: None

## Progress Updates

### 2026-01-23
Requirement drafted.
