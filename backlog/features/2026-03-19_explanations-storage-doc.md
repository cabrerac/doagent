---
id: "2026-03-19_explanations-storage-doc"
title: "Document explanation storage and retrieval model"
status: "Proposed"
priority: "Medium"
created: "2026-03-19"
last_updated: "2026-03-19"
category: "features"
related_cips:
- "0006"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- interpretability
- documentation
---

# Task: Document explanation storage and retrieval model

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Document current explanation storage and retrieval behaviour in the library and analysis output, then propose and document target structure if gaps are found.

Current behaviour to capture:
- `interpretability.get_explanations_for(record_id, run_id, ...)` retrieval path
- relationship between outcome, agent_update, and explanation records
- linkage via provenance (`derived_from`) and trace (`enabled_by_id`)
- output artifact `analysis/interpretability/explanations_for_last.json`
- explanation payload linkage to decisions (`decision_id`)

## Alternatives Considered

- **Alternative A:** Keep behaviour implicit in code only.
- **Alternative B:** Publish explicit explanation schema + retrieval contract in docs.

**Selected:** Alternative B.

**Rationale:** Improves maintainability and user understanding, reduces ambiguity for future contributors.

## Acceptance Criteria

- [ ] Current explanation record shape and retrieval logic are documented in user-facing docs.
- [ ] Documentation clarifies where explanation data lives during/after runs.
- [ ] If gaps exist, a proposed target schema/storage approach is documented with rationale.
- [ ] Links to this explanation doc are added from README analysis section and/or interpretability docs.

## Implementation Notes

Focus first on accurate documentation of existing behaviour before proposing changes. Any schema/storage changes discovered should be tracked via follow-up CIP/backlog items.

## Related

- CIP: 0006
- PRs: N/A
- Documentation: doagent/analysis/interpretability.py, README.md, guides/*

## Progress Updates

### 2026-03-19

Task created from previous session handoff item: "How explanations are stored (and how they should be)". This backlog task now tracks the work in VibeSafe artifacts.
