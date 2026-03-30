---
id: "2026-03-28_notebook-restructuring-llm-integration"
title: "Restructure notebooks and local runners with actual LLM integration"
status: "Ready"
priority: "High"
created: "2026-03-28"
last_updated: "2026-03-28"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies:
- "2026-03-28_pluggable-llm-policy"
- "2026-03-28_update-notebooks-factorization-idk"
tags:
- backlog
- notebooks
- local-runners
- llm
- policy-factorization
- idk
- talk
---

# Task: Restructure notebooks and local runners with actual LLM integration

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Restructure the three demo notebooks and local example runners so the narrative flows naturally from simple policies to LLMs, policy factorisation, and IDK. LLM policies use **actual LLM clients** (not mocks).

The restructuring was motivated by the observation that the abstain section in `01_minimal_demo` felt bolted on. The agreed narrative arc: **simple policies → LLM policies → policy factorisation → IDK as a product of reasoning**.

### 01_minimal_demo.ipynb

- **Remove** Step 8 (abstain section). The minimal demo is the "hello world" — pure mechanics only.
- **Keep** Steps 1–7 as-is (install, import, config, env, wrap, decide, inspect).

### 02_push_demo.ipynb + local runner

- **Keep** the main heuristic run and analysis sections unchanged.
- **Add** an LLM comparison section after the analysis:
  - Swap one agent's policy to the LLM-backed one.
  - Run a few steps showing `reasoning` in the records alongside `choice`.
  - Show an IDK event (LLM abstains); inspect it.
  - Compare heuristic records vs LLM records side by side via `session.inspect("agent_update")`.

### 03_gridworld_demo.ipynb + local runner

- The LLM-based policy **replaces** one agent from the start — it is a first-class participant, not an add-on.
- **Four agents, four distinct policies:** `grid_random`, `grid_frontier`, `grid_auction_frontier`, `grid_llm`.
- Agent mapping:
  - agent_0: `grid_frontier`
  - agent_1: `grid_random`
  - agent_2: `grid_auction_frontier`
  - agent_3: `grid_llm` (replaces the second `grid_random`)
- The notebook reflects this from the beginning (policy definitions, agent configs, run loop, analysis).
- The `grid_llm` policy uses `llm_decide_factory` with a gridworld-specific `build_prompt`.

### Shared LLM infrastructure (example code, not library)

- **`examples/llm_policy.py`**: Add a `create_llm_tool()` helper that reads `GEMINI_API_KEY` (or `DOAGENT_GEMINI_API_KEY`) from env and creates the LLM callable using the Google Gemini SDK (`google-genai`). Also supports OpenAI as an alternative provider.
- **google-genai SDK** is an optional dependency for examples only — users running heuristic-only demos don't need it. Default model: `gemini-3.1-flash-lite-preview` (free tier).
- **Error handling**:
  - Local runners: clear error ("Set GEMINI_API_KEY to run the LLM agent").
  - Notebooks: graceful skip with a printed message so the rest of the notebook still runs.

### Files to change

| File | Change |
|---|---|
| `notebooks/01_minimal_demo.ipynb` | Remove Step 8 (abstain section) |
| `notebooks/02_push_demo.ipynb` | Add LLM comparison section after analysis |
| `notebooks/03_gridworld_demo.ipynb` | Replace agent_3 with grid_llm from the start |
| `examples/llm_policy.py` | Add `create_llm_tool()` helper |
| `examples/gridworld_demo/policies.py` | Add `llm_explore_policy` using `llm_decide_factory` with gridworld-specific `build_prompt` |
| `examples/gridworld_demo/gridworld_demo.py` | Import and register `grid_llm`, wire LLM tool creation |
| `examples/gridworld_demo/gridworld_demo_config.yaml` | Change agent_3 to `grid_llm` |
| `examples/push_demo/push_demo.py` | (Optional) Add LLM comparison to local runner |

## Acceptance Criteria

- [ ] 01_minimal_demo is a clean hello-world with no abstain section.
- [ ] 02_push_demo has a working LLM comparison section (with actual LLM client).
- [ ] 03_gridworld_demo has 4 distinct policies including grid_llm from the start.
- [ ] Local runners reflect the same changes as the notebooks.
- [ ] LLM policies use actual clients (OpenAI SDK via env var).
- [ ] Graceful skip in notebooks when no API key is set.
- [ ] Clear error in local runners when no API key is set.
- [ ] Full test suite passes.

## Implementation Notes

Design decisions from deliberation:

- **Talk narrative**: The notebooks mirror the talk arc — DOAgent addresses intellectual debt in MAS; simple policies show the framework; LLM policies add observable reasoning (factorisation); IDK emerges from reasoning.
- **"Agentic AI" framing**: Delivered implicitly through code — the same API and records for heuristic and LLM policies. LLMs enable natural-language policy factorisation but the coordination/architecture are established MAS patterns.
- **Sorrento talk**: `sorrento-doagent.md` created in `cabrerac.github.io` repo with the full talk structure and snippets. The notebooks are the reproducible backing for the talk.
- **`create_llm_tool()` design**: Reads env var, imports `openai` (deferred import), creates a callable `(*, model, messages) -> str`. Zero library dependency — example code only.
- **Gridworld `build_prompt`**: Understands position, cells, width, height, shared_map, and the 5-action space (stay/left/right/up/down).

## Related

- CIP: [0002](../../cip/cip0002_shared-data-model.md)
- Parent task: [2026-03-27_talk-policy-factorization-idk-library](./2026-03-27_talk-policy-factorization-idk-library.md)
- Depends on: [2026-03-28_pluggable-llm-policy](./2026-03-28_pluggable-llm-policy.md), [2026-03-28_update-notebooks-factorization-idk](./2026-03-28_update-notebooks-factorization-idk.md)
- Talk source: `cabrerac.github.io/scripts/generate_content/talks-sources/sorrento-doagent.md`

## Progress Updates

### 2026-03-28

Task created from deliberation session. All design decisions documented above. Ready for Stage 3 (per-task alternatives) and Stage 4 (implementation).
