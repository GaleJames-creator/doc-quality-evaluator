#!/usr/bin/env python3
"""
check_docs.py

Structural and editorial checks for the documentation in this repository.

Complements codespell rather than duplicating it. codespell finds misspelled
words; these checks find defects in correctly spelled text:

  * repeated words          "The The evaluator" — an insertion landing twice
  * decapitalized starts    ". his applies"     — an edit clipping a capital
  * broken relative links   a moved or renamed page
  * missing anchors         a heading that no longer exists
  * raw dashes in prose     house style requires &mdash;/&ndash; entities
  * stray periods           `page`. or No. in a table cell, from an
                            operating system text substitution

Reads .md, .mdx, .yaml, and .yml. YAML is included because an OpenAPI
`summary` or `description` is published documentation once a site generator
renders it, so a typo there reaches readers. The dash rule is Markdown-only;
see DASH_EXTS.

The repeated-word and decapitalized-start checks exist because codespell
catches neither: every word involved is spelled correctly.

Code fences and inline code spans are excluded from the prose checks, so
console output, YAML samples, and command examples are never flagged.

Usage:
    python3 tools/check_docs.py            # check the default file set
    python3 tools/check_docs.py docs/      # check specific files or folders

Exit code is 0 when clean and 1 when any check fails, so it can gate CI.
"""

from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Prose we maintain. Verbatim evaluator output (report_samples/sample_*,
# txt_samples/, json_samples/) is deliberately excluded: it records what the
# model actually returned, typos included, and must not be edited to suit a
# linter. samples/ is excluded because those files are evaluation inputs.
DEFAULT_PATHS = ["README.md", "CHANGELOG.md", "docs", "knowledge_base",
                 "report_samples/README.md"]
SKIP_PARTS = {".git", "chroma_db", "node_modules", "__pycache__", "images",
              "samples", "txt_samples", "json_samples"}
SKIP_NAMES = {"sample_ci_report.md", "sample_batch_report.md",
              "ci_report.md", "batch_report.md"}

DOC_EXTS = (".md", ".mdx", ".yaml", ".yml")

# The dash rule is a Markdown authoring convention, so it applies to Markdown
# only. YAML is read by code generators and specification viewers that render an
# HTML entity literally, and knowledge base files are chunked into the model
# prompt, where "&mdash;" arrives as those eight characters. Both keep real
# dashes. The text checks still apply everywhere: an OpenAPI `description` is
# published documentation and a repeated word in one ships to readers.
DASH_EXTS = (".md", ".mdx")
DASH_EXEMPT_DIRS = {"knowledge_base", "agent"}

# House style sets dash entities closed: word&mdash;word, no surrounding spaces.
# One exception: a table cell whose entire content is a dash keeps its padding,
# because there the dash marks "not applicable" rather than punctuating a
# sentence, and `| &mdash; |` is simply how such a cell is written.
DASH_ENTITIES = ("&mdash;", "&ndash;")

# A period that arrived by accident rather than by intent. macOS substitutes
# ". " for a double space when "Add period with double-space" is on, and padding
# a table cell to align its pipes is exactly a double-space keystroke. The result
# lands in parameter names and required flags, reads as deliberate, and no spell
# checker objects, because a period is valid text.
#
# The signature is a single-token cell ending in a period: `page`. or No. or
# Type. A one-word cell needs no terminal punctuation, so the period is almost
# always the substitution. Multi-word cells end in periods legitimately and are
# left alone.
STRAY_PERIOD = re.compile(r"^\S+\.$")

# Abbreviations that are legitimately a whole cell.
PERIOD_OK = {"e.g.", "i.e.", "etc.", "vs.", "cf.", "approx."}

# Lowercase fragments that are real words missing a leading capital. Kept
# deliberately short: a word that legitimately starts a sentence in lowercase
# (such as "here" or "or") would produce false positives.
DECAPITALIZED = {  # codespell:ignore
    "his", "hese", "hey", "hat", "hich", "ith", "nd", "herefore",  # codespell:ignore
    "owever", "lso", "dditionally", "ecause", "efore", "fter", "hen",  # codespell:ignore
}


def display(path: Path) -> Path:
    """Path relative to the repository root, or absolute if it lives outside."""
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def find_files(paths: list[str]) -> list[Path]:
    """Expand paths into Markdown files, skipping generated and sample content."""
    out: set[Path] = set()
    for raw in paths:
        # Resolve a relative path against the working directory, the way every
        # other command line tool does. Resolving against ROOT instead means
        # running this script from another repository silently checks a
        # same-named file in this one and reports it clean.
        p = Path(raw) if os.path.isabs(raw) else Path.cwd() / raw
        if not p.exists():
            # Fall back to the default paths' home so `check_docs.py docs/`
            # still works when invoked from elsewhere in this repository.
            fallback = ROOT / raw
            if fallback.exists():
                p = fallback
        if p.is_dir():
            candidates = sorted(f for e in DOC_EXTS for f in p.rglob(f"*{e}"))
        else:
            candidates = [p] if p.is_file() else []
        for f in candidates:
            parts = display(f).parts[:-1]
            # Dot-directories (.git, .github, .claude) hold configuration and
            # workflows, not documentation.
            if any(part.startswith(".") for part in parts):
                continue
            if SKIP_PARTS & set(parts) or f.name in SKIP_NAMES:
                continue
            out.add(f)
    return sorted(out)


def prose_lines(path: Path):
    """
    Yield (line_number, masked_prose, raw_line) for lines outside a code fence.

    Code spans become "@" rather than an empty string. Deleting them outright
    joins the words on either side, so "such as `x` as shown" collapses to
    "such as as shown" and trips the repeated-word check. "@" is not a word
    character and not sentence-ending, so it breaks adjacency without
    disturbing the other checks. The raw line is yielded alongside it for the
    checks that need the original text, such as the stray-period check, which
    reports the offending cell back to the reader.
    """
    in_fence = False
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        yield n, re.sub(r"`[^`]*`", "@", line), line


def slug(text: str) -> str:
    """
    Approximate GitHub's heading-to-anchor conversion.

    HTML entities are decoded first, so a heading reads the same to this
    function whether it was written with a literal character or an entity.
    Without that step, converting an em dash in a heading to `&mdash;` would
    silently change the computed anchor and report every working link to it
    as broken.
    """
    text = html.unescape(text)
    text = re.sub(r"[`*]", "", text)
    text = "".join(c for c in text if c.isalnum() or c in " -_")
    return text.strip().lower().replace(" ", "-")


def heading_slugs(path: Path) -> set[str]:
    out, in_fence = set(), False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        m = None if in_fence else re.match(r"^#{1,6} (.+)$", line)
        if m:
            out.add(slug(m.group(1)))
    return out


def _stray_periods(text: str) -> list[str]:
    """
    Return table cells that appear to have gained a period by accident.

    Only table rows are examined. Elsewhere a trailing period is ordinary
    punctuation, and flagging it would bury the real finding in noise.
    """
    if not text.lstrip().startswith("|"):
        return []
    out = []
    for cell in text.strip().strip("|").split("|"):
        cell = cell.strip()
        if not STRAY_PERIOD.match(cell) or cell.lower() in PERIOD_OK:
            continue
        # Non-ASCII tokens here are mojibake, not punctuation. A document about
        # encoding problems legitimately shows corrupted text in a before-and-
        # after table, and that is a different defect than a stray period.
        if not cell.isascii():
            continue
        out.append(cell)
    return out


def _spaced_entities(text: str) -> list[str]:
    """
    Return dash entities that carry a space on either side.

    A table row is examined cell by cell, so a cell holding nothing but a dash
    keeps its padding without being reported. Everywhere else the whole line is
    one segment.
    """
    if text.lstrip().startswith("|"):
        segments = text.strip().strip("|").split("|")
    else:
        segments = [text]

    found = []
    for seg in segments:
        if seg.strip() in DASH_ENTITIES:
            continue
        for entity in DASH_ENTITIES:
            if f" {entity}" in seg or f"{entity} " in seg:
                found.append(entity)
    return found


def check_prose(path: Path) -> list[str]:
    """Repeated words, decapitalized sentence starts, and raw dashes."""
    problems = []
    rel = display(path)
    check_dashes = (path.suffix in DASH_EXTS
                    and not DASH_EXEMPT_DIRS & set(rel.parts))
    for n, text, raw in prose_lines(path):
        for m in re.finditer(r"\b(\w+)\s+\1\b", text, re.IGNORECASE):
            # Repeated digit groups are normal in test data: card numbers like
            # 4242 4242 4242 4242, routing numbers, phone numbers, IDs. A
            # doubled word is a typo; a doubled number is usually the point.
            if m.group(1).isdigit():
                continue
            problems.append(f"{rel}:{n}: repeated word: '{m.group(0)}'")
        for cell in _stray_periods(raw):
            problems.append(
                f"{rel}:{n}: stray period in table cell: '{cell}'")
        for m in re.finditer(r"(?:^|[.!?]\s+)([a-z]\w*)", text):
            if m.group(1) in DECAPITALIZED:
                problems.append(
                    f"{rel}:{n}: sentence starts with '{m.group(1)}' "
                    f"(missing a leading capital?)")
        # Headings are exempt from both dash rules. A heading's text generates
        # its anchor, and other pages link to that anchor, so changing one risks
        # a broken cross-reference for a cosmetic gain. Platforms differ in
        # whether they slug the rendered text or the raw source, and that
        # difference is not worth discovering after publishing.
        if check_dashes and not text.lstrip().startswith("#"):
            if "—" in text or "–" in text:
                problems.append(
                    f"{rel}:{n}: raw dash in prose; use &mdash; or &ndash;")
            for entity in _spaced_entities(text):
                problems.append(
                    f"{rel}:{n}: spaced {entity}; house style sets it closed")
    return problems


def check_links(path: Path, all_files: list[Path]) -> list[str]:
    """
    Relative links resolve, and anchors exist in the target file.

    Reads the same masked prose as the other checks, so a link written inside
    a code span or a fenced block as an example is not resolved against the
    filesystem and reported as broken.
    """
    problems = []
    rel = display(path)
    base = path.parent
    prose = "\n".join(text for _, text, _raw in prose_lines(path))
    for link in re.findall(r"\]\(([^)\s]+)\)", prose):
        if link.startswith(("http://", "https://", "mailto:", "#!")):
            continue
        # A leading slash is a site route resolved by the documentation
        # platform (Mintlify, Docusaurus), not a path on disk. Checking it
        # against the filesystem reports every valid cross-page link as broken.
        if link.startswith("/"):
            continue
        target_path, _, frag = link.partition("#")
        target = (base / target_path).resolve() if target_path else path
        # Site generators link without a file extension, so `[x](development)`
        # means development.mdx. Try both before calling a link broken.
        if target_path and not target.exists():
            for ext in (".md", ".mdx"):
                candidate = target.with_name(target.name + ext)
                if candidate.exists():
                    target = candidate
                    break
        if not target.exists():
            problems.append(f"{rel}: link target missing: {link}")
        elif frag and target.suffix in (".md", ".mdx") and frag not in heading_slugs(target):
            problems.append(f"{rel}: anchor not found: {link}")
    return problems


def main(argv: list[str]) -> int:
    files = find_files(argv or DEFAULT_PATHS)
    if not files:
        print("No Markdown files matched.", file=sys.stderr)
        return 1

    problems: list[str] = []
    for f in files:
        problems += check_prose(f)
        problems += check_links(f, files)

    if problems:
        print(f"check_docs: {len(problems)} problem(s) in {len(files)} file(s)\n")
        for p in problems:
            print(f"  {p}")
        return 1

    print(f"check_docs: {len(files)} file(s) checked, no problems found.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
