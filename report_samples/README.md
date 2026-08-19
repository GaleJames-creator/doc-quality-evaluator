# Report samples

Saved output from the CI runner and the batch runner, so you can see what the evaluator produces without installing anything or spending API credits. Each file is unedited output, copied from a real run.

## When to use them

Read these to see the report format before wiring the evaluator into your own project: the per-file score table, the collapsible per-criterion feedback, and the pass/fail status against the threshold. Between them, the two samples cover both outcomes&mdash;every file passing, and a file below the gate. A run that skips or excludes files adds a "Skipped files" list that neither sample shows.

These are point-in-time snapshots, not live results. They are refreshed deliberately rather than on every run&mdash;the working reports (`ci_report.md` and `batch_report.md`) are generated output and remain outside version control.

## Available documents

* [Sample CI report](./sample_ci_report.md)&mdash;seven changed files scored against a threshold of 3, one below the gate. This is the report the GitHub Action posts as a pull request comment. Generated 29 July 2026.
* [Sample batch report](./sample_batch_report.md)&mdash;three documents in `samples/` scored in a single run, including an OpenAPI YAML specification, all above the gate. This is the report `evaluate_batch.py --report` writes. Generated 13 August 2026.

## Regenerating

```text
python3 ci/evaluate_changed.py                                              # writes ci_report.md
python3 evaluate_batch.py samples/ --report report_samples/sample_batch_report.md
```

Copy `ci_report.md` over `sample_ci_report.md` when you want to refresh the CI sample.

---

[Back to the doc-quality-evaluator README](../README.md)
