# Failure attribution experiment

This paper evaluation runs a three-agent addition team with a known failure.

**D** is native DOAgent records. **W** and **T** are independent baselines
under `baselines/who_when` and `baselines/trace_elephant`. Those collectors
are the capture methods scored in the paper tables. D0 and D1 are thinner
views of the same D2 records.

Two tables, never mixed:

1. **Attribution (paired).** One D2 execution writes full records. Observe-only
   W and T collectors write their packs from that same run. D0 and D1 are
   projected from D2 (thinner evidence, same gold). Judges score W, T, D0,
   D1, and D2. Lookup uses full D2.
2. **Capture cost (unpaired).** Five executions: W-only, T-only (no DOAgent;
   the loop passes values between policies), and live D0, D1, and D2.
   Time includes writing the capture log. Bytes count only that log
   (`who_when.json`, `trace_elephant.json`, or `records/`). Gold, manifest,
   and analysis files are written after the clock and are not counted.

Lookup on D is reported beside the LLM judges, not as a fourth prompting
style. Judge methods are all-at-once, step-by-step, and binary search.

From the repository root:

```bash
python -m experiments.attribution.run
python -m experiments.attribution.run --observe
python -m experiments.runners.attribution_comparison
python -m experiments.runners.attribution_comparison --table accuracy
python -m experiments.attribution.judge output/<run_id>
```

The run and `--table cost` commands are deterministic and need no API key.
`--observe` and `--table accuracy` attach W and T as watchers on one D2
run. `--table cost` times W, T, D0, D1, and D2. `--table accuracy` then
judges the collector packs plus projected D0/D1 and native D2.
`--table both` runs cost first, then accuracy.

The judge command reads `OPENAI_API_KEY` or `DOAGENT_OPENAI_API_KEY`.
Tests use a fake client and make no network calls.

A file run writes `gold.json` and `manifest.json` in `output/<run_id>/`.
Views, lookup, judge results, and scores go under
`output/<run_id>/analysis/attribution/`. Collector packs are
`who_when.json` and `trace_elephant.json`. D views are `d0.json`,
`d1.json`, and `d2.json`. The prompt receives task information but never
receives `gold_who`, `gold_when`, or the planted-fault description.

`scores.json` compares each judge method on W, T, D0, D1, and D2 with
gold, and places lookup beside those methods with zero judge tokens.

The requested model, model identifier returned by the provider, temperature,
per-call responses, and token counts are saved with each result. The released
Who&When code names `gpt-4o` without a dated snapshot, so the returned model
identifier is important reproducibility metadata.
