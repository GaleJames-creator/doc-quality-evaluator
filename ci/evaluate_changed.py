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
  python3 ci/evaluate_changed.py -v              # include feedback for every doc
  python3 ci/evaluate_changed.py -q              # score table only, no feedback

By default the console output shows the score table plus feedback for failing
docs only. -v/--verbose shows feedback for all docs; -q/--quiet shows just the
table. These flags affect stdout only — the Markdown report (and the PR comment)
always contains the full per-criterion feedback.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Import the shared core from the repo root regardless of where this is invoked.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluate_core import (  # noqa: E402
    CRITERIA,
    evaluate_document,
    get_collection,
    is_evaluation_skipped,
)

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


def changed_docs(explicit_files: list[str] | None = None) -> list[str]:
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
    elif explicit_files:
        # Local run with explicit file arguments.
        candidates = explicit_files
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


def _fmt(score) -> str:
    """Format a score for display, tolerating strings, None, and missing values."""
    if isinstance(score, bool):  # guard: bool is a subclass of int
        return str(score)
    if isinstance(score, (int, float)):
        return f"{score:g}"
    return str(score) if score not in (None, "") else "?"


def _criterion(result: dict, name: str):
    """
    Return (score, feedback) for a criterion, tolerating malformed model output.

    The tool schema asks for each criterion as a {score, feedback} object, but the
    model can occasionally return a bare string or number instead. This never
    raises: a non-dict entry yields no score and its text as feedback.
    """
    entry = result.get(name) if isinstance(result, dict) else None
    if isinstance(entry, dict):
        return entry.get("score"), str(entry.get("feedback", "") or "").strip()
    if entry is None:
        return None, ""
    return None, str(entry).strip()


def _skipped_note(skipped: list[str]) -> str:
    joined = ", ".join(f"`{p}`" for p in skipped)
    return f"_Skipped via `skip-evaluation`: {joined}_"


def render_report(
    results: list[tuple[str, dict]],
    errors: list[tuple[str, str]],
    skipped: list[str] | None = None,
) -> str:
    skipped = skipped or []
    lines = [MARKER, "## Documentation quality report", ""]

    if not results and not errors:
        lines.append("No documentation files required evaluation in this pull request.")
        if skipped:
            lines.append("")
            lines.append(_skipped_note(skipped))
        return "\n".join(lines) + "\n"

    total = len(results) + len(errors)
    summary = (
        f"Evaluated {total} changed documentation file(s) against the knowledge "
        f"base. Threshold: overall score ≥ **{THRESHOLD:g}**."
    )
    if skipped:
        summary += f" {len(skipped)} file(s) skipped via `skip-evaluation`."
    lines.append(summary)
    lines.append("")

    # Summary table.
    header = ["File", "Overall"] + [c.capitalize() for c in CRITERIA] + ["Status"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")

    for path, result in results:
        overall = _overall_score(result)
        cells = [f"`{path}`", f"{overall:g}/5" if overall is not None else "?"]
        for c in CRITERIA:
            score, _ = _criterion(result, c)
            cells.append(_fmt(score))
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
            score, feedback = _criterion(result, c)
            lines.append(f"- **{c.capitalize()} ({_fmt(score)}/5):** {feedback}")
        overall_entry = result.get("overall") if isinstance(result, dict) else None
        summary = (str(overall_entry.get("summary", "") or "").strip()
                   if isinstance(overall_entry, dict) else str(overall_entry or "").strip())
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

    if skipped:
        lines.append(_skipped_note(skipped))
        lines.append("")

    lines.append("---")
    lines.append(
        "_Generated by the doc-quality-evaluator GitHub Action "
        "(RAG-grounded, model: claude-haiku-4-5)._"
    )
    return "\n".join(lines) + "\n"


_ABBR = {"clarity": "Clr", "completeness": "Cmp", "accuracy": "Acc",
         "consistency": "Con", "structure": "Str"}


def _is_fail(result: dict) -> bool:
    ov = _overall_score(result)
    return ov is None or ov < THRESHOLD


def render_console(
    results: list[tuple[str, dict]],
    errors: list[tuple[str, str]],
    skipped: list[str] | None = None,
    feedback: str = "failures",
) -> str:
    """Render an aligned, fixed-width table for terminal/CI-log readability.

    The Markdown report (render_report) is what gets posted as the PR comment;
    this plainer version is only what prints to stdout, where Markdown pipes are
    hard to scan. Variable-width File column comes last so the numbers stay aligned.

    `feedback` controls the detail block under the table:
      "failures" (default) — feedback only for docs that fail the gate
      "all"                 — feedback for every doc
      "none"                — no feedback, table only
    """
    skipped = skipped or []
    head = (f"{'Status':<6} {'Overall':>7}  "
            + "  ".join(f"{_ABBR[c]:>3}" for c in CRITERIA) + "  File")
    out = [f"Documentation quality — threshold: overall >= {THRESHOLD:g}", "",
           head, "-" * len(head)]

    def row(status: str, overall, scores, path: str) -> str:
        ov = f"{overall:g}".rjust(7) if isinstance(overall, (int, float)) else str(overall).rjust(7)
        cols = "  ".join(_fmt(s).rjust(3) for s in scores)
        return f"{status:<6} {ov}  {cols}  {path}"

    for path, result in results:
        ov = _overall_score(result)
        status = "PASS" if ov is not None and ov >= THRESHOLD else "FAIL"
        scores = [_criterion(result, c)[0] for c in CRITERIA]
        out.append(row(status, ov if ov is not None else "?", scores, path))
    for path, _msg in errors:
        out.append(row("ERROR", "-", ["-"] * len(CRITERIA), path))
    for path in skipped:
        out.append(row("SKIP", "-", ["-"] * len(CRITERIA), path))

    # Per-file feedback under the table (controlled by `feedback`).
    if feedback != "none":
        shown = results if feedback == "all" else [(p, r) for p, r in results if _is_fail(r)]
        if shown:
            heading = "Feedback" if feedback == "all" else "Feedback (failing docs)"
            out += ["", heading, "-" * len(heading)]
            for path, result in shown:
                ov = _overall_score(result)
                status = "PASS" if ov is not None and ov >= THRESHOLD else "FAIL"
                ov_str = _fmt(ov) if ov is not None else "?"
                out += ["", f"{path}  ({status}, overall {ov_str}/5)"]
                for c in CRITERIA:
                    score, fb = _criterion(result, c)
                    out.append(f"  {c.capitalize()} ({_fmt(score)}/5): {fb}")
                entry = result.get("overall") if isinstance(result, dict) else None
                summary = (str(entry.get("summary", "") or "").strip()
                           if isinstance(entry, dict) else str(entry or "").strip())
                if summary:
                    out.append(f"  Overall ({ov_str}/5): {summary}")

    if errors:
        out += ["", "Errors", "------"]
        for path, msg in errors:
            out.append(f"  {path}: {msg}")

    if skipped:
        out += ["", "Skipped via skip-evaluation: " + ", ".join(skipped)]

    return "\n".join(out)


# ── Step outputs ─────────────────────────────────────────────────────────────

def set_output(name: str, value: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def _parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Evaluate changed documentation and gate on quality.")
    parser.add_argument("files", nargs="*",
                        help="Specific docs to evaluate (local runs only).")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-q", "--quiet", action="store_true",
                       help="Print the score table only (no feedback).")
    group.add_argument("-v", "--verbose", action="store_true",
                       help="Print feedback for every doc, not just failures.")
    return parser.parse_args(argv)


def main() -> int:
    args = _parse_args(sys.argv[1:])
    feedback_mode = "all" if args.verbose else "none" if args.quiet else "failures"

    docs = changed_docs(args.files)
    skipped = [d for d in docs if is_evaluation_skipped(d)]
    to_evaluate = [d for d in docs if d not in set(skipped)]

    if skipped:
        print("Skipping (skip-evaluation): " + ", ".join(skipped))

    if not to_evaluate:
        report = render_report([], [], skipped)
        Path(REPORT_PATH).write_text(report, encoding="utf-8")
        print("No documentation files require evaluation — nothing to score.")
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

    for path in to_evaluate:
        print(f"Evaluating {path} ...")
        try:
            result = evaluate_document(path, collection=collection)
            results.append((path, result))
        except Exception as exc:  # noqa: BLE001 — report any failure per-file
            print(f"  error: {exc}", file=sys.stderr)
            errors.append((path, str(exc).splitlines()[0]))

    report = render_report(results, errors, skipped)
    Path(REPORT_PATH).write_text(report, encoding="utf-8")
    print("\n" + render_console(results, errors, skipped, feedback=feedback_mode))

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
