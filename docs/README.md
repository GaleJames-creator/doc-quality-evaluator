# Documentation

Guides and reference material for the `doc-quality-evaluator`. The repository [README](../README.md) covers prerequisites and setup; these pages cover everything after that.

## When to use them

Read the explanation pages to understand what the evaluator does and how far to trust it, the how-to guides to run it against your own documentation, and the reference pages to look up a format, field, or error message.

## Available documents

### Explanation

* [How it works](./how-it-works.md) &mdash; the evaluation pipelines, status messages, retrieval diagnostics, and scoring
* [Interpreting evaluator feedback](./interpreting-feedback.md) &mdash; score ranges, common false positives, and known limitations

### How-to guides

* [Batch evaluation](./batch-evaluation.md) &mdash; score a folder in one run, choose a threshold, and exclude files
* [Continuous integration](./continuous-integration.md) &mdash; score changed docs on every pull request
* [Customization](./customization.md) &mdash; adapt the system prompt and knowledge base to your own standards

### Reference

* [Supported formats](./supported-formats.md) &mdash; Markdown, MDX, OpenAPI YAML, and `docType` classification
* [Output reference](./output-reference.md) &mdash; the JSON structure and what each field means
* [Troubleshooting](./troubleshooting.md) &mdash; errors, warnings, and what they mean

---

[Back to the doc-quality-evaluator README](../README.md)
