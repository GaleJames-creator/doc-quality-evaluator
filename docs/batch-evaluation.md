# Batch evaluation

`evaluate_batch.py` evaluates a set of documentation files&mdash;Markdown, MDX, and OpenAPI YAML&mdash;in one run. Unlike the CI runner, it accepts files and folders anywhere on disk, with no `DOC_PATHS` restriction and no git involvement, so you can score an entire docs folder before opening a pull request or audit a documentation set that lives outside this repository.

## Prerequisites

* The setup in the [repository README](../README.md) completed: dependencies installed, an Anthropic API key in `.env`, and `python3 build_index.py` run at least once. The batch runner needs the index, and reports `Error: Collection 'doc_guidelines' not found` without it.
* Python 3.10 or later. The batch runner uses type annotations that raise a `TypeError` on import under earlier versions.

## Usage

> **Important**: Every file found is sent to the model and billed, so run `--dry-run` first to check what a folder actually contains before pointing the runner at it. Target your docs folders directly rather than a repository root. Files are scored one at a time, so a large run takes minutes rather than seconds.

Pass any mix of files and folders. Folders are searched recursively for `.md`, `.mdx`, `.yaml`, and `.yml` files, skipping dependency and hidden directories (`node_modules`, `.git`, `.github`, and any other dot-directory) so a run over a docs repository doesn't score hundreds of vendored READMEs and CI configs. Pass `--all` to include them.

```text
python3 evaluate_batch.py samples/                       # every doc in a folder
python3 evaluate_batch.py docs/ api/openapi.yaml         # mix folders and files
python3 evaluate_batch.py samples/*.md -v                # shell globs work too
python3 evaluate_batch.py docs/ --dry-run                # preview the file set
python3 evaluate_batch.py docs/ --report batch_report.md # saves the report to a Markdown file
python3 evaluate_batch.py docs/ --threshold 4            # temporarily changes the evaluation threshold
```

The runner prints an aligned score table with one row per file, followed by per-criterion feedback. By default, feedback appears only for docs that fail the gate; `-v`/`--verbose` shows it for every doc and `-q`/`--quiet` shows only the table. Pass `--report FILE` to also write the full Markdown report&mdash;the same format the CI runner posts as a PR comment.

## Options

| Option            | Default                          | Purpose                                                                             |
| ----------------- | -------------------------------- | ----------------------------------------------------------------------------------- |
| `--threshold`     | `3` (or `DOC_QUALITY_THRESHOLD`) | Minimum passing `overall` score (1&ndash;5). Applies to that run only.              |
| `--report FILE`   | off                              | Write the full Markdown report to `FILE`.                                           |
| `--all`           | off                              | Include dependency and hidden directories when searching folders.                   |
| `--exclude GLOB`  | none                             | Exclude files matching `GLOB`. Repeatable. Adds to `.docqualityignore`.             |
| `--dry-run`       | off                              | List the file set and each file's disposition, then exit without calling the API.   |
| `-v`, `--verbose` | off                              | Print feedback for every doc, not just failures.                                    |
| `-q`, `--quiet`   | off                              | Print the score table only.                                                         |

## Choosing a threshold

`--threshold` applies to the run it's passed to and nothing else. Nothing is written to disk; the next run without the flag returns to the default, and the CI gate is unaffected because the workflow reads `DOC_QUALITY_THRESHOLD` from its own environment. Raise it freely to see what a stricter bar would flag.

Set the two independently:

* **CI gate: `3`.** The gate should catch real regressions without failing pull requests on noise. Because scores vary by up to a point between runs on identical content (see [Expect run-to-run variance](interpreting-feedback.md#expect-run-to-run-variance)), a gate at `4` fails docs that are genuinely fine&mdash;a quickstart scored 3.5 and 4.0 on consecutive runs with no edits.
* **Personal target: `4`.** Run `--threshold 4` locally as a periodic polish lens, never as a gate. Treat the result as a worklist, not a verdict, and act on feedback that persists across runs rather than any single score. Documents scoring between 4.0 and 4.4 flip between pass and fail across runs with no edits, so a gate at this level is nondeterministic by construction.

## Excluding files

There are two ways to keep a file out of an evaluation run. Which one to use depends on where the file is read.

**Use `.docqualityignore` or `--exclude` for files that render on GitHub.** GitHub displays YAML frontmatter in `.md` files as a small table at the top of the rendered page, so adding `skip-evaluation: true` to a repository `README.md`, `CONTRIBUTING.md`, or similar puts a stray `skip-evaluation | true` table in front of every visitor. External exclusion keeps the file's rendered output clean. It's also the right choice for files consumed by other tooling&mdash;agent system prompts, context files&mdash;where an unexpected frontmatter block could end up inside the content the tool reads.

**Use `skip-evaluation: true` frontmatter for pages inside a docs site.** Static site generators such as Mintlify consume frontmatter to build pages and ignore keys they don’t recognize, so the flag remains invisible to readers. Frontmatter also travels with the file, which is what you want for a page that the evaluator should never be scored regardless of who runs the evaluator. It is the only mechanism the CI runner honors.

To exclude files by pattern, create a `.docqualityignore` file in the folder you point the runner at:

```text
# Repository meta files: frontmatter would render on GitHub
README.md
CONTRIBUTING.md
AGENTS.md

# Assistant system prompts and context, not developer documentation
agent/
```

One glob pattern per line. Blank lines and lines beginning with `#` are ignored. Each pattern is matched against the file's path relative to the folder and against its bare filename, so `README.md` matches at any depth while `agent/*.md` matches only that folder. A pattern ending in `/` excludes a directory and everything under it.

For one-off runs, pass `--exclude` instead. It's repeatable and adds to whatever `.docqualityignore` already contains:

```text
python3 evaluate_batch.py . --exclude 'README.md' --exclude 'agent/*.md'
```

Excluded files appear in the run as `skip ... (excluded)`, so an exclusion is always visible rather than silent. Confirm your patterns with `--dry-run` before a real run.

Exclusion patterns apply only to files found by folder recursion. A file you name explicitly on the command line is always evaluated, even if a pattern matches it&mdash;asking for a file by name is a clearer signal than a pattern written earlier.

## Behavior

* Folder recursion skips `node_modules` and dot-directories by default; explicitly named files are always evaluated, wherever they live.
* Files matching `--exclude` or `.docqualityignore` are excluded and reported with an "excluded" reason. See [Excluding files](#excluding-files).
* Files with `skip-evaluation: true` in the frontmatter are skipped and listed exactly as in CI.
* Files with no evaluable content after frontmatter and MDX stripping&mdash;for example, spec-driven pages whose body is only frontmatter and component references&mdash;are skipped with a "no evaluable content" note instead of erroring, and don't fail the gate. Score the underlying OpenAPI spec directly to cover their content.
* YAML files must be OpenAPI or Swagger specs (see [OpenAPI YAML handling](supported-formats.md#openapi-yaml-handling)). Non-spec YAML found during folder recursion&mdash;linter rulesets, CI workflows&mdash;is skipped with a "not an OpenAPI spec" note and doesn't fail the gate. An explicitly named non-spec YAML is still reported as an error, since silently skipping a file you asked for by name would hide a mistake.
* A file that errors doesn't stop the run&mdash;it's reported in the table, and the run continues.
* The exit code is `1` when any file scores below the threshold or errors, and `0` otherwise, so the batch runner can gate scripts the same way the CI check gates PRs.

---

[Back to the doc-quality-evaluator README](../README.md)
