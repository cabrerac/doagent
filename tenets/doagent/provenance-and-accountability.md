---
id: "provenance-and-accountability"
title: "Provenance and Accountability"
status: "Active"
created: "2026-01-22"
last_reviewed: "2026-01-22"
review_frequency: "Weekly"
conflicts_with: []
tags:
- tenet
- doagent
---

# Tenet: Provenance and Accountability

## Tenet

**Description**: Every decision should be traceable to inputs, tools, and agents. The system must make it practical to reconstruct why an action happened and who or what influenced it, even in decentralised settings.

**Quote**: *"If it matters, it must be traceable."*

**Examples**:
- Each agent write includes source references and reason metadata.
- Data changes carry lineage links to upstream artifacts.
- Auditors can replay a decision path from stored events.

**Counter-examples**:
- Agent outputs that cannot be linked to data sources.
- Decision chains that are only stored in volatile logs.
- Missing attribution when multiple agents collaborate.

**Conflicts**:
- Potential conflict with raw performance or minimal storage.
- Resolution: allow configurable retention while keeping core provenance fields.
