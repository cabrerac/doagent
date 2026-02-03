---
id: "2026-02-02_record-envelope-provenance"
title: "Define record envelope and provenance schema"
status: "Completed"
priority: "High"
created: "2026-02-02"
last_updated: "2026-02-02"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- shared-data
---

# Task: Define record envelope and provenance schema

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Define the record envelope and the provenance schema for shared data records. Document required and optional fields and their meaning.

## Acceptance Criteria
- [ ] Record envelope fields are documented with clear semantics.
- [ ] Provenance schema includes sources and tools fields.

## Implementation Notes
Ensure changes remain backwards compatible with `SimpleRecord`.

## Related
- CIP: 0002
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-02-02
Task created.

### 2026-02-02
Set to In Progress. Drafting record envelope and provenance schema.

### 2026-02-02
Defined provenance with `contributions` entries, each tied to a single agent with sources/tools/notes.

### 2026-02-02
Marked complete using the simplest contribution model. A richer multi-agent mapping may be needed later.
