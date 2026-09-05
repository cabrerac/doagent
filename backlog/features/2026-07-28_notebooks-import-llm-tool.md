---
id: "2026-07-28_notebooks-import-llm-tool"
title: "Notebooks import create_llm_tool instead of repeating it"
status: "Ready"
priority: "Medium"
created: "2026-07-28"
last_updated: "2026-07-28"
category: "features"
related_cips:
- "0011"
owner: "Christian Cabrera"
dependencies:
- "2026-07-28_single-source-llm-provider-config"
tags:
- backlog
- llm
- notebooks
---

# Task: Notebooks import create_llm_tool instead of repeating it

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

`notebooks/02_push_demo.ipynb` and `notebooks/03_gridworld_demo.ipynb` each rebuild the LLM tool inline — reading the
key, importing the SDK, defining the call. The same logic already exists in `examples/llm_policy.py`, so it lives in
three places and can drift apart. It already has: the notebooks default to `gpt-4o` in their own copies.

Have the notebooks import `create_llm_tool` and keep only what is genuinely notebook-specific, which is reading the
key from Colab secrets and falling back to a heuristic policy when no key is set.

## Acceptance Criteria

- [ ] Both notebooks import `create_llm_tool` rather than defining their own.
- [ ] Colab secret handling still works.
- [ ] Without a key, the notebooks still run and fall back as they do today.
- [ ] The model and provider match what the examples use, with no separate default hidden in a notebook.
- [ ] Both notebooks run end to end.

## Implementation Notes

The notebooks install the package from GitHub, so they can import from `examples/` only if that path is available. If
it is not, the fix may be to have the notebook fetch the helper the same way it fetches other example code — worth
checking before assuming a plain import works.

Do this after the provider config task, so the notebooks import a helper that already reads provider from config.

## Related

- CIP: [0011](../../cip/cip0011_llm-agents.md)
- Depends on: [2026-07-28_single-source-llm-provider-config](./2026-07-28_single-source-llm-provider-config.md)
- Code: `notebooks/02_push_demo.ipynb`, `notebooks/03_gridworld_demo.ipynb`, `examples/llm_policy.py`

## Progress Updates

### 2026-07-28

Task created when CIP-0011 was accepted. Duplication found during verification: the notebooks carry their own copies
of the LLM tool with their own model defaults.
