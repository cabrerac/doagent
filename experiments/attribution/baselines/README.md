# Attribution baselines

Independent collectors for the paper comparison. They are **not** part of
the `doagent` library. Each baseline has its own subfolder.

| Folder | Role | Paper analogue |
|---|---|---|
| `who_when/` | Output-only logger | Who&When conversation / output logs |
| `trace_elephant/` | Step input/output interceptor | TraceElephant static capture |

JSON keys stay short (`w`, `t`). Pack files are `who_when.json` and
`trace_elephant.json`.

**Paired attribution.** Attach both collectors as observers on one
DOAgent D2 run. They must not feed the team. Judges score those collector
packs plus D0, D1, and D2 from that same execution. D0 and D1 are
downsampled from D2.

**Unpaired capture cost.** Five executions. Live D0, D1, and D2 use
DOAgent and do not attach collectors. The Who&When-only and
TraceElephant-only runs do **not** use DOAgent: same policies, host loop
passes each return value to the next agent, collector only logs. W and T
are not the mailbox. Time includes writing the capture log. Bytes count
only that log. Do not include judges, and do not require the five runs
to share gold.

## References

- Zhang et al., *Which Agent Causes Task Failures and When?*,
  [arXiv:2505.00212](https://arxiv.org/abs/2505.00212);
  [dataset/code](https://github.com/ag2ai/Agents_Failure_Attribution)
- Chen et al., *Seeing the Whole Elephant* (TraceElephant),
  [arXiv:2604.22708](https://arxiv.org/abs/2604.22708);
  [code](https://github.com/TraceElephant/TraceElephant)
