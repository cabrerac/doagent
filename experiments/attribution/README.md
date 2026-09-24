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
2. **Capture cost (unpaired).** Five conditions: W-only, T-only (no DOAgent;
   the loop passes values between policies), and live D0, D1, and D2.
   Time includes writing the capture log. Bytes count only that log
   (`who_when.json`, `trace_elephant.json`, or `records/`). Gold, manifest,
   and analysis files are written after the clock and are not counted.

Lookup on D is reported beside the LLM judges, not as a fourth prompting
style. Judge methods are all-at-once, step-by-step, and binary search.

## Repetition

The two tables repeat for different reasons, so `config.yaml` has separate
counts under `repeats`:

| Setting | What repeats | What it measures |
|---|---|---|
| `cost` | executions of each capture condition | time and bytes on disk, which need a fresh execution each time |
| `executions` | paired attribution executions | one trajectory each, so different evidence per execution |
| `judge` | judge passes over one execution's stored packs | judge variation on fixed evidence |

Results keep every measurement rather than only the average, so both sources
of variation stay visible.

## Running

From the repository root:

```bash
python -m experiments.attribution.run
python -m experiments.attribution.run --observe
python -m experiments.runners.attribution_comparison
python -m experiments.runners.attribution_comparison --table accuracy
python -m experiments.runners.attribution_comparison --table both
python -m experiments.attribution.judge output/<run_id>
```

The single run and `--table cost` are deterministic and need no API key.
`--observe` attaches W and T as watchers on one D2 run. `--table cost` times
all five conditions. `--table accuracy` runs the paired executions and judges
the collector packs plus projected D0/D1 and native D2. `--table both` runs
cost first, then accuracy.

Repeat counts come from the config and can be overridden for a cheap run:

```bash
python -m experiments.runners.attribution_comparison --table cost --cost-repeats 3
python -m experiments.runners.attribution_comparison --table accuracy --judge-passes 1
python -m experiments.runners.attribution_comparison --table accuracy \
    --campaign output/attribution_campaign_<stamp>
```

`--campaign` adds results to a campaign folder that already exists, so the
cost and attribution tables can be produced by separate commands.

The judge command reads `LITE-LLM_API_KEY` from the environment or from a
`.env` file at the repository root, and sends it to the university proxy.
It accepts `--methods`, `--views`, and `--label` for a single cheaper pass.
Tests use a fake client and make no network calls.

## Output

A campaign owns one folder:

```
output/attribution_campaign_<stamp>/
    runs/          one folder per execution
    cost.csv       one row per capture execution
    accuracy.csv   one row per judged view, method, and judge pass
    summary.json   aggregates, repeat counts, and provenance
    plots/         figures drawn from the two CSV files
```

Both CSV files are long format: one row is one measurement, with the
condition, repeat, and run identifier beside it, so any number can be traced
back to the records that produced it. `summary.json` adds the aggregates
(median, mean, 10th and 90th percentile, min, max, deviation for timings;
accuracy fractions and token spread per method and view), the git commit, and
a fingerprint of the settings.

Each execution folder holds `gold.json`, `manifest.json`, `records/`, and
`analysis/attribution/` with the collector packs (`who_when.json`,
`trace_elephant.json`), the D views (`d0.json`, `d1.json`, `d2.json`), and
lookup. Repeated judge passes are kept separately as `judges_pass01.json`
and `scores_pass01.json`, so no pass overwrites another.

The prompt asks when the failure becomes inevitable, given each agent's
job. It receives the task and the team roster. It does not receive
`gold_who`, `gold_when`, or the planted-fault description.

`scores.json` compares each judge method on W, T, D0, D1, and D2 with gold,
and places lookup beside those methods with zero judge tokens.

The requested model, model identifier returned by the provider, temperature,
per-call responses, and token counts are saved with each result. The released
Who&When code names `gpt-4o` without a dated snapshot, so the returned model
identifier is important reproducibility metadata.

## Figures

The campaign runner draws whatever tables it just wrote, as PNG for viewing
and PDF for papers. To redraw later:

    python -m experiments.attribution.plots output/attribution_campaign_<stamp>

- `capture_cost` — wall-clock time as a strip of repeats with a median mark,
  and log size on disk as a median bar, per evidence pack.
- `attribution_accuracy` — agent-level and step-level accuracy per judging
  method and evidence pack, with lookup as its own group.
- `tokens_against_accuracy` — both accuracies against judge tokens, where
  lookup sits on the zero-token axis.

Use `--formats png` or `--formats pdf` to write only one of the two.

## Next experiment

The same two tables run on the five-agent team in `experiments/magentic_one/` with `--team magentic_one`.
The crate campaign `attribution_campaign_20260923_004741` scored at the ceiling.
The next who and when case should follow a Who&When dataset execution as closely as possible.
Whether a fully described dataset execution can be replayed here is still open.
