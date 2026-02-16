---
id: "2026-02-16_adapter-contract-dedup"
title: "Document adapter contract for state deduplication"
status: "Proposed"
priority: "Medium"
created: "2026-02-16"
last_updated: "2026-02-16"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies:
- "2026-02-16_state-dedup-contract"
tags:
- backlog
- adapter
- documentation
---

# Task: Document adapter contract for state deduplication

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Document the adapter contract for state deduplication. Adapters that support outcome deduplication must implement state lookup (state_hash -> outcome_id). Document how JSON, database, and stream adapters can fulfil this contract, and what optional methods or hooks the adapter interface requires.

## Acceptance Criteria

- [ ] Adapter contract doc specifies: when dedup is expected, how state_hash is computed.
- [ ] Contract describes optional vs required behaviour for adapters.
- [ ] JSON: in-memory or sidecar index. DB: native indexes. Streams: medium-specific approach.
- [ ] Contract is linked from data model spec and state-dedup-contract.

## Implementation Notes

- Add to docs/ or extend existing adapter documentation.
- Keep contract minimal; adapters that do not implement dedup can skip (no index, always create new outcomes).

## Related

- CIP: 0002
- PRs: N/A
- Documentation: State dedup contract, data model spec

## Progress Updates

### 2026-02-16
Task created. Part of REQ-0001/CIP-0002 iteration 2 backlog.
