# Doc quality evaluator

The `doc-quality-evaluator` (evaluator) uses Python and the Anthropic API to assess doc quality quickly. It streamlines reviews while leaving final judgment to editors. It provides two evaluation modes: `baseline` and `RAG-enhanced`.

## `Baseline` evaluation

The `evaluate.py` script uses Python and the Anthropic API to score documentation using a structured system prompt quickly.

All doc samples in the [portfolio](https://github.com/GaleJames-creator/gale-james) were evaluated using this tool before publishing.

## `RAG-enhanced` evaluation

The `evaluate_rag.py` script uses Python with RAG enhancement to score documentation against structured criteria grounded in a local knowledge base. RAG (retrieval-augmented generation) is a technique that grounds AI responses in your own reference material instead of relying only on the model's general training. The evaluator indexes your documentation standards in ChromaDB &mdash; a local vector store, meaning a database that indexes text by meaning rather than keywords &mdash; retrieves the guidelines most relevant to the doc being evaluated, and injects them into the evaluation prompt.

All doc samples in the [Mintlify portfolio](https://galejames.mintlify.app) were evaluated using this tool before publishing.

## Assumptions

This guide assumes basic familiarity with Git, Python, and the command line.

## Prerequisites

* Python 3.10 or later. The batch runner, the report renderer, and the CI runner use `X | None` type annotations, which raise a `TypeError` on import under Python 3.9 and earlier.
* Git &mdash; needed to clone the `doc-quality-evaluator` repository.
* A code editor, such as VS Code, or a plain-text editor for editing files. You run the evaluator from the terminal.
* An Anthropic API account and API key. Limit access to your Anthropic key to those who need it. Do not store it in a version control system. When you add it to the `.env` file, it's never pushed to your GitHub repository.

> **API costs**: An Anthropic API key is required. Anthropic accounts receive a small amount of starter credits for API calls. After that, usage is billed per token. The cost to run the evaluator against a typical doc is a fraction of a cent per evaluation. See [Anthropic's pricing page](https://claude.com/pricing) for current rates.

## Setup

1. Clone the `doc-quality-evaluator` repository to your machine.
2. Run `pip install -r requirements.txt` in your local Python environment to install the evaluator's Python dependencies.
3. Add a `.env` file to the root level of the cloned repository and include your Anthropic key.

    ```text
    ANTHROPIC_API_KEY=your-actual-key-here
    ```

4. Run `python3 build_index.py` to index the `knowledge_base/` folder into the local ChromaDB vector store. Rerun it any time you add or update knowledge base files.

    ```text
    python3 build_index.py
    ```

    Required by `evaluate_rag.py`, `evaluate_batch.py`, and the CI runner. Only the `baseline` evaluator runs without it. Skipping this step produces `Error: Collection 'doc_guidelines' not found`.

5. Preview what a run would evaluate, without calling the API or spending anything.

    ```text
    python3 evaluate_batch.py samples/ --dry-run
    ```

6. Score the sample documents.

    ```text
    python3 evaluate_batch.py samples/
    ```

    You'll get a score table, feedback for anything below the threshold, and an exit code of `0` or `1`. See [Batch evaluation](./docs/batch-evaluation.md) for thresholds, reports, and exclusions.

7. Point the evaluator at your own documentation. Files are read wherever they live, so there's no need to copy anything into `samples/`. Always dry-run an unfamiliar folder first &mdash; every file found is sent to the model and billed.

    ```text
    python3 evaluate_batch.py ~/my-docs/ --dry-run
    python3 evaluate_batch.py ~/my-docs/
    ```

To score a single document instead, pass its path to `evaluate_rag.py`:

```text
python3 evaluate_rag.py ~/my-docs/quickstart.mdx
```

![`RAG-enhanced` output example](./images/RAG_enhanced_output_sample.png)

## Which tool should I use?

| You want to | Use | Needs the index |
| ----------- | --- | --------------- |
| Score a folder, or gate a script on documentation quality | `evaluate_batch.py` | Yes |
| Score one document while you're editing it | `evaluate_rag.py` | Yes |
| Score changed docs on every pull request | `ci/evaluate_changed.py`, through the GitHub Action | Yes |
| Compare grounded scoring against the original ungrounded scorer | `evaluate.py` | No |

Start with `evaluate_batch.py`. The `RAG-enhanced` evaluator supersedes the `baseline` one: it grounds its feedback in your knowledge base, reads `docType` to grade against the right checklist, and returns structured output rather than JSON embedded in text &mdash; which is why it isn't subject to the parse errors the `baseline` script can still hit. `evaluate.py` is kept because comparing the two shows what retrieval grounding actually adds; see [Comparing `baseline` and `RAG-enhanced` JSON results](./docs/output-reference.md#comparing-baseline-and-rag-enhanced-json-results).

## What's here

| Path                            | Contents                                                         |
| ------------------------------- | ---------------------------------------------------------------- |
| `evaluate.py`                   | `Baseline` evaluator: one file, one API call, no retrieval        |
| `evaluate_rag.py`               | `RAG-enhanced` evaluator: retrieves guidelines, then scores      |
| `evaluate_batch.py`             | Batch runner: many files in one run, with a pass/fail gate        |
| `evaluate_core.py`              | Shared evaluation logic used by the RAG, batch, and CI runners   |
| `report.py`                     | Console table and Markdown report rendering                      |
| `build_index.py`                | Indexes `knowledge_base/` into the local ChromaDB vector store   |
| `ci/evaluate_changed.py`        | CI runner: scores changed docs on a pull request                 |
| `tools/check_docs.py`           | Proofreading and link checks that run without the model          |
| `knowledge_base/`               | The documentation standards the evaluator grades against         |
| `samples/`                      | Sample documents to evaluate, including an OpenAPI specification |
| `report_samples/`               | Saved output from a real CI run and a real batch run             |
| `json_samples/`, `txt_samples/` | Saved evaluation results in JSON and plain text                  |
| `images/`                       | Pipeline diagrams and output screenshots                         |
| `.docqualityignore`             | Files excluded from batch evaluation                             |

## Sample output

To see what the evaluator produces before installing anything, read the [saved report samples](./report_samples/README.md): a [batch report](./report_samples/sample_batch_report.md) covering the documents in `samples/`, and a [CI report](./report_samples/sample_ci_report.md) with one file below the quality gate.

## Documentation

Start here, then follow the guide that matches what you want to do.

### Understand the tool

* [How it works](./docs/how-it-works.md) &mdash; the evaluation pipelines, status messages, retrieval diagnostics, and scoring
* [Interpreting evaluator feedback](./docs/interpreting-feedback.md) &mdash; score ranges, common false positives, and known limitations

### Run an evaluation

* [Batch evaluation](./docs/batch-evaluation.md) &mdash; score a folder in one run, choose a threshold, and exclude files
* [Continuous integration](./docs/continuous-integration.md) &mdash; score changed docs on every pull request
* [Customization](./docs/customization.md) &mdash; adapt the system prompt and knowledge base to your own standards

### Look something up

* [Supported formats](./docs/supported-formats.md) &mdash; Markdown, MDX, OpenAPI YAML, and `docType` classification
* [Output reference](./docs/output-reference.md) &mdash; the JSON structure and what each field means
* [Troubleshooting](./docs/troubleshooting.md) &mdash; errors, warnings, and what they mean
* [Changelog](./CHANGELOG.md) &mdash; what changed and when

## Roadmap

This document is primarily written to help developers get up and running with the `doc-quality-evaluator` and to clearly explain the technical details you need. Refer to this roadmap for future evaluator features.

1. **RAG evaluation**: Completed July 2026. Read and evaluate Markdown and MDX files using RAG and output a report.
2. **MDX support**: Completed July 2026. Extend format support to `.mdx` files.
3. **Batch evaluation**: Completed August 2026. Read and evaluate a set of files (Markdown, MDX, and OpenAPI YAML) and output a report (see [Batch evaluation](docs/batch-evaluation.md)).
4. **Markdown report generation**: Completed July 2026. The CI runner generates a Markdown report of per-file scores and feedback (see [Continuous integration](docs/continuous-integration.md)).
5. **Word document support**: Extend format support to `.docx` files using python-docx.
6. **Scoring thresholds and pass/fail behavior**: Completed July 2026. A configurable overall-score threshold flags and fails evaluation when a doc scores below it, enforced in the CI gate.
7. **GitHub Action integration**: Completed July 2026. The evaluator runs on every pull request, comments on the scores, and fails the check if the score is below the threshold (see [Continuous integration](docs/continuous-integration.md)).
8. **Line-level feedback**: Include line numbers in evaluation feedback to help writers locate specific issues without manual searching.
9. **Changelog and release-note document types**: Add checklists for both to `knowledge_base/diataxis_types.md` and accept them as `docType` values. Changelogs sit outside the five Diátaxis types, so the API-reference rubric scores them 1 on completeness and structure no matter how well written they are &mdash; the reason they're excluded from evaluation today rather than scored. A rubric that fits them would grade what actually matters: whether breaking changes are labeled, whether deprecations carry a sunset date and migration path, and whether entries describe what changed rather than listing commits.
10. **Snippet resolution**: Resolve MDX `import` statements before evaluation so reusable snippets are graded in the pages that include them. Snippet content is currently evaluated nowhere &mdash; imports are stripped, so it's absent from the including page and is scored out of context when evaluated on its own (see [Known limitations](docs/interpreting-feedback.md#known-limitations)).
11. **Exclusions in the CI runner**: Honor `.docqualityignore` and `--exclude` in `ci/evaluate_changed.py`, which currently recognizes only the `skip-evaluation` frontmatter flag. Until then, keep `DOC_PATHS` pointed at a documentation folder rather than a repository root.
