#!/usr/bin/env python3
"""
ci/evaluate_changed.py

GitHub Actions runner for the documentation quality evaluator.

On a pull request it:
  1. Determines which documentation files changed (added/modified) versus the
     PR base branch.
  2. Scores each with evaluate_core.evaluate_document().
  3. Writes a Markdown report (ci_report.md) that the workflow posts as a
     sticky PR comment.
  4. Reports pass/fail via step outputs and a non-zero exit so the workflow can
     turn the check red when any doc scores below the threshold.

Configuration (environment variables):
  GITHUB_BASE_REF        PR base branch (set automatically by GitHub Actions).
                         When unset, the script runs locally against files
                         passed as arguments, or every doc under DOC_PATHS.
  DOC_PATHS              Directory holding the docs under evaluation.
                         Default: "samples".
  DOC_QUALITY_THRESHOLD  Minimum acceptable "overall" score (1–5). Default: 3.
  DOC_QUALITY_REPORT     Output path for the Markdown report.
                         Default: "ci_report.md".
  GITHUB_OUTPUT          Step-output file (set automatically by GitHub Actions).

Local usage:
  python3 ci/evaluate_changed.py                 # evaluate all docs under DOC_PATHS
  python3 ci/evaluate_changed.py samples/x.mdx   # evaluate specific files
"""

import os
import subprocess
import sys
from pathlib import Path

# Import the shared core from the repo root regardless of where this is invoked.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluate_core import CRITERIA, evaluate_document, get_collection  # noqa: E402

DOC_PATHS   = os.environ.get("DOC_PATHS", "samples")
THRESHOLD   = float(os.environ.get("DOC_QUALITY_THRESHOLD", "3"))
REPORT_PATH = os.environ.get("DOC_QUALITY_REPORT", "ci_report.md")
DOC_EXTS    = (".md", ".mdx")
MARKER      = "<!-- doc-quality-report -->"


# ── Determine which docs to evaluate ─────────────────────────────────────────

def _is_doc(path: str) -> bool:
    p = Path(path)
    return (
        p.suffix in DOC_EXTS
        and str(p).replace(os.sep, "/").startswith(f"{DOC_PATHS}/")
        and p.is_file()
    )


def changed_docs() -> list[str]:
    """Return the doc files to evaluate for this run."""
    base = os.environ.get("GITHUB_BASE_REF")

    if base:
        # Pull request: diff HEAD against the base branch.
        subprocess.run(["git", "fetch", "origin", base], check=False,
                       capture_output=True)
        diff = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=d",
             f"origin/{base}...HEAD"],
            capture_output=True, text=True, check=False,
        )
        candidates = diff.stdout.split()
    elif len(sys.argv) > 1:
        # Local run with explicit file arguments.
        candidates = sys.argv[1:]
    else:
        # Local run: evaluate everything under DOC_PATHS.
        candidates = [str(p) for p in Path(DOC_PATHS).rglob("*") if p.suffix in DOC_EXTS]

    return sorted({c for c in candidates if _is_doc(c)})


# ── Report rendering ─────────────────────────────────────────────────────────

def _overall_score(result: dict):
    try:
        return float(result["overall"]["score"])
    except (KeyError, TypeError, ValueError):
        return None


def render_report(results: list[tuple[str, dict]], errors: list[tuple[str, str]]) -> str:
    lines = [MARKER, "## Documentation quality report", ""]

    if not results and not errors:
        lines.append("No documentation files changed in this pull request.")
        return "\n".join(lines) + "\n"

    total = len(results) + len(errors)
    lines.append(
        f"Evaluated {total} changed documentation file(s) against the knowledge "
        f"base. Threshold: overall score ≥ **{THRESHOLD:g}**."
    )
    lines.append("")

    # Summary table.
    header = ["File", "Overall"] + [c.capitalize() for c in CRITERIA] + ["Status"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")

    for path, result in results:
        overall = _overall_score(result)
        cells = [f"`{path}`", f"{overall:g}/5" if overall is not None else "?"]
        for c in CRITERIA:
            try:
                cells.append(f"{result[c]['score']:g}")
            except (KeyError, TypeError):
                cells.append("?")
        status = "Pass" if overall is not None and overall >= THRESHOLD else "Fail"
        cells.append(f"**{status}**")
        lines.append("| " + " | ".join(cells) + " |")

    for path, _msg in errors:
        cells = [f"`{path}`", "—"] + ["—"] * len(CRITERIA) + ["**Error**"]
        lines.append("| " + " | ".join(cells) + " |")

    lines.append("")

    # Per-file feedback in collapsible sections.
    for path, result in results:
        overall = _overall_score(result)
        lines.append(f"<details><summary><code>{path}</code> — feedback</summary>")
        lines.append("")
        for c in CRITERIA:
            entry = result.get(c, {})
            score = entry.get("score", "?")
            feedback = entry.get("feedback", "").strip()
            lines.append(f"- **{c.capitalize()} ({score}/5):** {feedback}")
        summary = result.get("overall", {}).get("summary", "").strip()
        lines.append(f"- **Overall ({overall:g}/5):** {summary}"
                     if overall is not None else f"- **Overall:** {summary}")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    if errors:
        lines.append("### Files that could not be evaluated")
        lines.append("")
        for path, msg in errors:
            lines.append(f"- `{path}`: {msg}")
        lines.append("")

    lines.append("---")
    lines.append(
        "_Generated by the doc-quality-evaluator GitHub Action "
        "(RAG-grounded, model: claude-haiku-4-5)._"
    )
    return "\n".join(lines) + "\n"


# ── Step outputs ─────────────────────────────────────────────────────────────

def set_output(name: str, value: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    docs = changed_docs()

    if not docs:
        report = render_report([], [])
        Path(REPORT_PATH).write_text(report, encoding="utf-8")
        print("No documentation files changed — nothing to evaluate.")
        set_output("changed", "false")
        set_output("result", "pass")
        return 0

    # Reuse one collection handle across all files.
    try:
        collection = get_collection()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    results: list[tuple[str, dict]] = []
    errors: list[tuple[str, str]] = []

    for path in docs:
        print(f"Evaluating {path} ...")
        try:
            result = evaluate_document(path, collection=collection)
            results.append((path, result))
        except Exception as exc:  # noqa: BLE001 — report any failure per-file
            print(f"  error: {exc}", file=sys.stderr)
            errors.append((path, str(exc).splitlines()[0]))

    report = render_report(results, errors)
    Path(REPORT_PATH).write_text(report, encoding="utf-8")
    print("\n" + report)

    # Gate: fail if any file scored below threshold or could not be evaluated.
    below = [p for p, r in results
             if (_overall_score(r) is None) or (_overall_score(r) < THRESHOLD)]
    failed = bool(below or errors)

    set_output("changed", "true")
    set_output("result", "fail" if failed else "pass")

    if failed:
        detail = ", ".join(below + [p for p, _ in errors])
        print(f"\nQuality gate FAILED (threshold {THRESHOLD:g}): {detail}", file=sys.stderr)
        return 1

    print(f"\nQuality gate PASSED (threshold {THRESHOLD:g}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
