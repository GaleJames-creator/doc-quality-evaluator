# Continuous integration

The evaluator runs automatically on pull requests through the GitHub Action defined in `.github/workflows/doc-quality.yml`. On every PR that changes a documentation file, the action scores the changed docs against the knowledge base, posts the results as a comment on the PR, and fails the check when any doc scores below a configurable threshold&mdash;turning the evaluator from a local script into an automated quality gate alongside your existing linting.

## Prerequisites

* The setup in the [repository README](../README.md) completed, including the knowledge base index. The CI runner needs it just as the local evaluators do.
* The repository hosted on GitHub, with permission to add repository secrets and edit workflow files.
* An Anthropic API key available as a repository secret &mdash; see [One-time setup](#one-time-setup).

## What the action does

When a pull request touches files under `samples/` (or the knowledge base, evaluator, or runner), the workflow checks out the branch, installs dependencies, rebuilds the ChromaDB index from `knowledge_base/`, and runs `ci/evaluate_changed.py`. The runner diffs the branch against the PR base, evaluates only the changed documentation files, and writes a Markdown report. The workflow posts that report as a single sticky comment&mdash;updated in place on later pushes rather than added as a new comment each time&mdash;containing a per-file score table and collapsible per-criterion feedback. If any changed doc scores below the threshold, or cannot be evaluated, the check fails so the PR cannot be merged under branch protection.

## One-time setup

1. Add your Anthropic key as a repository secret named `ANTHROPIC_API_KEY` (**Settings → Secrets and variables → Actions → New repository secret**). The workflow reads the key from this secret; it is never committed.
2. (Optional) To block merges automatically, add a branch protection rule on `main` (**Settings → Branches**) that requires the **Doc quality** check to pass.

That is all that is required&mdash;the workflow triggers itself on the next pull request.

## Configuration

The workflow is configured through environment variables in the `Evaluate changed docs` step:

| Variable                | Default   | Purpose                                                                                 |
|-------------------------|-----------|-----------------------------------------------------------------------------------------|
| `DOC_QUALITY_THRESHOLD` | `3`       | Minimum acceptable `overall` score (1&ndash;5). Docs scoring below this fail the check. |
| `DOC_PATHS`             | `samples` | Directory holding the docs under evaluation.                                            |
| `ANTHROPIC_API_KEY`     | &mdash;   | Supplied from the repository secret; required for the model call.                       |

Cost is bounded because only the documentation files changed in the pull request are evaluated, using the low-cost `claude-haiku-4-5` model.

## Skipping non-API docs

The evaluator reviews documents against API- and developer-documentation standards, so pages that aren't API docs&mdash;portfolio overviews, process memos, changelogs&mdash;can score poorly and wrongly fail the gate. To exclude a file, add `skip-evaluation: true` to its frontmatter:

```yaml
---
skip-evaluation: true
---
```

The CI and batch runners skip any doc flagged this way: it isn't scored, doesn't count toward the pass/fail gate, and is listed under a short "Skipped" note so the exclusion is visible. If a pull request changes only skipped docs, the check passes with no comment. (The interactive CLI, `evaluate_rag.py`, ignores the flag and evaluates whatever file you explicitly give it.)

Frontmatter delimiters must be exactly `---` (three hyphens) on their own line, both opening and closing. A malformed delimiter &mdash; two hyphens, or content before the opening line &mdash; causes the flag to go unread with no error raised, and the file is scored as ordinary content. Confirm the flag took effect with `python3 evaluate_batch.py <path> --dry-run`, which lists each file's disposition without calling the API.

> **Important**: Which mechanism to use depends on where readers see the file, not on which file it is. A site generator such as Mintlify or Docusaurus consumes frontmatter when it builds the page, so the flag stays invisible and is safe to use. GitHub renders frontmatter in `.md` files as a table at the top of the page, so the flag is visible to every visitor on any Markdown file read there &mdash; a repository `README.md`, `CONTRIBUTING.md`, or `SECURITY.md`, an architecture decision record, a runbook, an agent prompt file. Exclude those by pattern instead; see [Excluding files](batch-evaluation.md#excluding-files).

The distinction matters more than the file name. A `docs/` folder browsed on GitHub needs pattern-based exclusion, while the same files published through a site generator can carry the frontmatter flag safely.

This repository's own `README.md` is excluded by pattern in `.docqualityignore` for exactly that reason. To score an excluded file deliberately, name it directly &mdash; `python3 evaluate_batch.py README.md` &mdash; since an explicitly named file overrides any exclusion pattern.

The CI and batch runners also automatically skip files with no evaluable content after frontmatter and MDX stripping &mdash; for example, spec-driven pages whose body is only frontmatter and component references. These appear in the "Skipped" note with a "no evaluable content" reason and don't fail the gate.

## Proofreading checks

A second workflow, `.github/workflows/docs-lint.yml`, runs on any pull request that touches Markdown. It needs no API key, finishes in seconds, and catches the mechanical defects the model-based evaluation is not designed to find.

It runs three checks, in two jobs so a link failure and a prose failure are distinguishable at a glance:

* **markdown-link-check** resolves every link, using `.github/mlc_config.json`.
* **codespell** flags misspelled words against a dictionary of common errors.
* **`tools/check_docs.py`** flags defects in correctly spelled text: repeated words (`The The evaluator`), sentences that lost a leading capital (`. his applies`), relative links whose target no longer exists, anchors pointing at headings that have been renamed, and raw em or en dashes where house style wants an HTML entity. It reads `.md`, `.mdx`, `.yaml`, and `.yml`, resolves extensionless links the way a site generator does (`[dev](development)` finds `development.mdx`), and ignores site-absolute routes such as `/reference/authentication`, which are resolved by the platform rather than the filesystem. Dot-directories are skipped, so workflow and configuration files aren't treated as prose.

YAML is included because an OpenAPI `summary` or `description` becomes published documentation once a site generator renders it &mdash; a repeated word there reaches readers exactly as one in Markdown would. The dash rule is the exception: it applies to Markdown only, since specifications are also read by code generators and specification viewers that render an HTML entity as its literal characters.

> **Important**: Converting a dash inside a heading changes the text the heading is built from, and some platforms derive the anchor differently from an entity than from a literal character. This checker decodes entities before computing anchors, so it treats both forms alike &mdash; but verify cross-references on your published site after converting a dash in any heading that other pages link to.

Running `check_docs.py` against a documentation set built for a site generator needs one adjustment. The dash rule assumes rendered Markdown, so files that are fed to a model as prompt text &mdash; agent system prompts, context files, a knowledge base &mdash; should be listed in `DASH_EXEMPT_DIRS` in the script, exactly as `knowledge_base/` is here. An HTML entity in prompt text reaches the model as the literal characters `&mdash;`.

The second script exists because codespell catches neither of the first two. Every word in those two examples is spelled correctly, so a dictionary-based checker passes them &mdash; both reached the published documentation and were found by a human reading the page.

> **Note**: A page that documents typo detection will contain example typos. Write them as inline code so the checker skips them; it ignores fenced blocks and code spans, which is also why console output and command examples never trigger a warning.

> **Important**: codespell was added to `requirements.txt` in August 2026. If you cloned the repository before then, rerun `pip install -r requirements.txt` &mdash; a completed setup from an earlier version doesn't include it.

Run them locally before pushing. codespell installs with the other dependencies through `pip install -r requirements.txt`. The two tools are independent: neither depends on the other, and you can run either one alone, in any order.

```text
python3 -m codespell_lib               # misspelled words
python3 tools/check_docs.py            # repeated words, links, anchors, dashes
python3 tools/check_docs.py docs/      # the same checks, scoped to one folder
npx markdown-link-check --config .github/mlc_config.json README.md
```

`check_docs.py` resolves links against the filesystem, which is instant and needs no network. `markdown-link-check` additionally requests every external URL, so it's slower and subject to the host being reachable. Run the first constantly and the second before publishing.

Two entries in `.github/mlc_config.json` suppress hosts that refuse automated requests: the Mintlify portfolio returns `403` to the checker's user agent, and `claude.com` refuses the connection outright. Both were confirmed reachable in a browser before being added, and that rule is recorded in the config &mdash; a link checker reporting `403` usually means a working link, so verify before silencing anything.

To run both in one line, and stop at the first failure:

```text
python3 -m codespell_lib && python3 tools/check_docs.py
```

To check documentation in another repository, point codespell at it and exclude that repository's dependencies:

```text
python3 -m codespell_lib ~/my-docs --skip='*/node_modules/*'
```

> **Important**: Target a documentation folder rather than a repository root, exactly as with [Batch evaluation](batch-evaluation.md). Pointed at a repository root, codespell reads every vendored package in `node_modules/` and reports thousands of misspellings in third-party code &mdash; none of them yours to fix, and all of them overwritten by the next `npm install`. This repository's `.codespellrc` skips those directories, but its patterns apply to whatever tree you point at, so a repository with its own exclusions needs its own `.codespellrc`.

### Check the scope before scanning an unfamiliar tree

Every tool here walks directories recursively, and a repository root is not a documentation folder. They differ in how much they protect you from that:

| Tool | Excludes dependencies by default | How to preview the scope |
| ---- | -------------------------------- | ------------------------ |
| `evaluate_batch.py` | Yes, including outside this repository | `--dry-run` lists every file and its disposition without calling the API |
| `tools/check_docs.py` | Yes, including outside this repository | Run it &mdash; it costs nothing and reports how many files it checked |
| `python3 -m codespell_lib` | Only what `.codespellrc` lists | None; scope the path or pass `--skip` |

codespell is the one to watch. It has no equivalent of `--dry-run`, and it reads a dependency tree happily. To see which files a run is actually reporting on, collapse the output to a file list:

```text
python3 -m codespell_lib ~/my-docs --skip='*/node_modules/*' | grep ' ==> ' | cut -d: -f1 | sort -u
```

The `grep` filter keeps only finding lines, so codespell's configuration header doesn't end up in the list.

If that list contains paths you don't maintain, narrow the target folder or extend `--skip` before reading any of the findings.

Their success output differs, which is worth knowing before you wonder whether a command did anything. codespell prints nothing when it finds no misspellings &mdash; silence means it passed. `check_docs.py` always prints a summary line, such as `check_docs: 14 file(s) checked, no problems found.` Both exit `0` on success and non-zero on failure.

Invoking codespell as `python3 -m codespell_lib` rather than `codespell` avoids a `command not found` error: pip installs console scripts to a user directory that isn't always on your `PATH`. The bare `codespell` command works too, if that directory is on yours.

Both exit non-zero on failure, so they gate the pull request the same way the quality check does. Verbatim evaluator output in `report_samples/`, `txt_samples/`, and `json_samples/` is excluded from both: those files record what the model actually returned, and correcting them to satisfy a linter would falsify the record. Knowledge base files skip the dash check alone, because they are injected into the model prompt rather than rendered, and an HTML entity would reach the model as literal text.

## Running the CI check locally

`ci/evaluate_changed.py` also runs outside CI, which is useful before opening a PR:

```text
python3 ci/evaluate_changed.py                 # evaluate every doc under DOC_PATHS
python3 ci/evaluate_changed.py samples/my-doc.mdx   # evaluate specific files
python3 ci/evaluate_changed.py -v              # feedback for every doc
python3 ci/evaluate_changed.py -q              # score table only
```

It prints an aligned score table to the terminal and writes the same Markdown report to `ci_report.md` (the source of the PR comment), and it exits non-zero when a doc is below the threshold. By default, the console shows the table plus feedback for failing docs only; `-v`/`--verbose` shows feedback for every doc, and `-q`/`--quiet` shows just the table. These flags affect the console output only&mdash;the Markdown report and PR comment always include the full feedback.

---

[Back to the doc-quality-evaluator README](../README.md)
