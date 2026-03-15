---
id: "2026-01-28_library-writes-run-metadata"
title: "Library creates run_id, folders (including ./output/), and metadata.json"
status: "Done"
priority: "High"
created: "2026-01-28"
last_updated: "2026-01-28"
category: "features"
related_cips: []
owner: "Christian Cabrera"
dependencies: []
tags:
  - backlog
  - metadata
  - run
  - analysis
---

# Task: Library writes run metadata (metadata.json) and creates run folders

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> This task unblocks the analysis module, which reads this metadata to resolve run_id to an access point.

## Description

The **library** owns creation of run identity and output layout. Run-related data (**scenario_name**, **output_base**, etc.) are part of the **session configuration**. When the user creates a session via **Session.from_config(config)** and the config describes a run with persisted output (e.g. file-backed storage and scenario_name), the library creates the **run_id**, the **metadata file** (metadata.json), and the **folders** (including `./output/`). The **Session** exposes **run_id** and **run path** so the user can retrieve them (e.g. for analysis or logging). No separate "start run" API; everything goes through session config and the Session object.

**Format reference:** See [2026-03-04_analysis-module-library.md](2026-03-04_analysis-module-library.md) § Run metadata format.

Summary:
- **Location:** `<output_base>/<run_id>/metadata.json`. Default output_base is `./output/` (library creates it if missing).
- **Records:** File-backed runs use subfolder `records/`; metadata includes `records_dir: "records"`.
- **Required fields:** `run_id`, `scenario_name`, `storage_type`, `metadata_schema_version` (use `1`). For file: `records_dir`. For mongo/stream: `config_ref` (named file config, not in git). Optional: `created_at` (ISO 8601).

## Run conventions (library owns, via session config)

- **Session config** includes run-related fields: e.g. `scenario_name` (e.g. `"gridworld"`, `"push"`), optional `output_base` (default `"./output"`). When config has file-backed (or other persisted) storage and scenario_name, **Session.from_config(config)** creates run_id in the form `<scenario_name>_run_<timestamp>_<short_uuid>` (e.g. `gridworld_run_20260315_192246_4f5cae2e`), output_base folder, run subfolder `./output/<run_id>/`, records subfolder `./output/<run_id>/records/`, and writes `metadata.json`.
- **Session** exposes **run_id** and **run path** (e.g. `session.run_id`, `session.run_path` or `session.output_path`) so the user can retrieve them and pass run_id to analysis. User gets run_id and path from the session, not from a separate API.
- **Runners** do not create output folders or run_id; they put scenario_name (and output_base if needed) in the config and get run_id and path from the session after creation.

## Acceptance Criteria

- [x] **Session configuration** accepts run-related fields: `scenario_name` (required for runs with output), optional `output_base` (default `"./output"`). These are part of the config passed to Session.from_config.
- [x] When **Session.from_config(config)** is called with file-backed (or other persisted) storage and `scenario_name`, the library creates the output base folder, generates run_id, creates the run subfolder and (for file) the records subfolder, writes `metadata.json` with all required fields, and configures the Session to write records to the created path.
- [x] **Session** exposes **run_id** and **run path** (e.g. `session.run_id`, `session.run_path`) so the user can retrieve them. User can pass session.run_id to analysis or log it.
- [x] Metadata format is valid JSON and conforms to the spec in the analysis module backlog task (`run_id`, `scenario_name`, `storage_type`, `metadata_schema_version`, `records_dir` for file, etc.).

## Implementation Notes

- Extend the config shape accepted by Session.from_config: add optional `scenario_name`, optional `output_base` (default `"./output"`). When shared_data is file (or persisted) and scenario_name is set, before creating the file adapter: generate run_id (e.g. UUID or timestamp-based), create output_base/run_id/ and output_base/run_id/records/, write metadata.json, then create FileSharedData pointing at the records path. Store run_id and run path on the Session instance and expose them as properties (e.g. run_id, run_path). When scenario_name is missing or storage is memory/noop, do not create folders or metadata; run_id and run_path may be None or absent.
- For in-memory runs, if the config includes scenario_name and an optional output path, the library may still create an output folder and write metadata with `storage_type: "memory"` so that run_id exists for reference; analysis will report that posterior analysis is not available for that run_id.

## Related

- **Unblocks:** [2026-03-04_analysis-module-library.md](2026-03-04_analysis-module-library.md) — analysis module reads this metadata to resolve run_id.
- **Format spec:** Run metadata format section in the analysis module backlog task (same file as above).

## Progress Updates

### 2026-03-15
Task created. Metadata format defined in analysis module backlog; this task implements the library side (writing metadata.json).

### 2026-03-15
Run conventions: library creates run_id, metadata file, and all folders (including ./output/). Runners supply scenario_name and do not create folders; library owns output layout.

### 2026-03-15
Session config: scenario_name and run-related data (e.g. output_base) are part of session configuration. Session.from_config creates run_id, folders, and metadata when config has persisted storage and scenario_name. Session exposes run_id and run path so the user can retrieve them (e.g. session.run_id, session.run_path).

### 2026-03-15
Implementation complete. Session.from_config accepts scenario_name and output_base; creates run_id, output_base/run_id/, records/ subfolder, and metadata.json when file + scenario_name; Session.run_id and Session.run_path exposed. Test added in test_session.py. Demos updated to use scenario_name + output_base (gridworld_demo, push_demo).

### 2026-03-15
Run folder naming: run_id (and folder name) set to `<scenario_name>_run_<timestamp>_<short_uuid>` (e.g. `gridworld_run_20260315_192246_4f5cae2e`) for clearer, scenario-aware output folders.
