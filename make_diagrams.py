#!/usr/bin/env python3
"""
make_diagrams.py

Generates the pipeline diagrams in images/ as SVG.

Run: python3 make_diagrams.py

Each diagram is described as data (lanes of boxes, or explicit node/edge
lists) and rendered by the helpers below, so layout is recomputed rather
than hand-maintained. Regenerate after changing a pipeline; do not hand-edit
the generated .svg files.
"""

from pathlib import Path

OUT = Path(__file__).parent / "images"

INK, SUB = "#1a1a1a", "#5c5c5c"
PALETTE = {
    "rag":   ("#fbe4f3", "#c9539f"),
    "batch": ("#e3f2e8", "#3f8f5f"),
    "ci":    ("#ece6fa", "#6b4fc9"),
    "muted": ("#f2f1ee", "#9c9890"),
}

HEAD = """<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="ttl desc">
<title id="ttl">{title}</title>
<desc id="desc">{desc}</desc>
<defs><marker id="arw" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
<path d="M0 0 L10 5 L0 10 z" fill="{sub}"/></marker></defs>
<style>
.t{{font:500 15px ui-sans-serif,system-ui,-apple-system,sans-serif;fill:{ink}}}
.s{{font:13px ui-sans-serif,system-ui,-apple-system,sans-serif;fill:{sub}}}
.chip{{font:600 12px ui-sans-serif,system-ui,-apple-system,sans-serif;fill:#fff;letter-spacing:.03em}}
.ln{{stroke:{sub};stroke-width:1.6;fill:none;marker-end:url(#arw)}}
</style>
<rect width="{w}" height="{h}" fill="#ffffff"/>
"""


def box(x, y, w, h, lines, kind="rag"):
    fill, stroke = PALETTE[kind]
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{stroke}" stroke-width="1.8"/>']
    cx = x + w / 2
    lh = 19
    top = y + h / 2 - (len(lines) - 1) * lh / 2 + 5
    for i, ln in enumerate(lines):
        cls = "t" if i == 0 else "s"
        out.append(f'<text x="{cx:.0f}" y="{top + i * lh:.0f}" class="{cls}" text-anchor="middle">{ln}</text>')
    return "\n".join(out)


def lane(x, y, w, h, label):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" stroke="{INK}" stroke-width="2.4"/>\n'
            f'<rect x="{x + 14}" y="{y - 13}" width="{24 + len(label) * 8.6:.0f}" height="26" rx="5" fill="{INK}"/>\n'
            f'<text x="{x + 20}" y="{y + 4}" class="chip">{label}</text>')


def arrow(x1, y1, x2, y2):
    return f'<path class="ln" d="M{x1:.0f} {y1:.0f} H{x2:.0f}"/>' if y1 == y2 else \
           f'<path class="ln" d="M{x1:.0f} {y1:.0f} L{x2:.0f} {y2:.0f}"/>'


def render_lane(x0, y0, steps, kind, bw=196, bh=104, gap=44):
    """Lay a single row of boxes left to right, connected by arrows."""
    parts, x = [], x0
    for i, lines in enumerate(steps):
        parts.append(box(x, y0, bw, bh, lines, kind))
        if i < len(steps) - 1:
            parts.append(arrow(x + bw + 6, y0 + bh / 2, x + bw + gap - 4, y0 + bh / 2))
        x += bw + gap
    return "\n".join(parts), x - gap


def write(name, w, h, title, desc, body):
    svg = HEAD.format(w=w, h=h, title=title, desc=desc, ink=INK, sub=SUB) + body + "\n</svg>\n"
    (OUT / name).write_text(svg, encoding="utf-8")
    print(f"wrote images/{name}  ({w}x{h})")


# ── 1. RAG-enhanced pipelines (corrected) ────────────────────────────────────

md_steps = [
    ["User provides", ".md file"],
    ["evaluate_rag.py", "reads the file"],
    ["Retrieve guidelines", "from knowledge_base", "+ guaranteed docType"],
    ["Anthropic API call", "(prompt + retrieved", "guidelines)"],
    ["Model evaluates", "against 5 criteria", "(1–5 scale)"],
    ["submit_evaluation", "tool call returns", "a parsed object"],
    ["Results printed", "to terminal"],
]
mdx_steps = ([["User provides", ".mdx file"]] + md_steps[1:2]
             + [["Strip MDX syntax", "before evaluation"]] + md_steps[2:])

body_a, end_a = render_lane(64, 92, md_steps, "rag")
body_b, end_b = render_lane(64, 330, mdx_steps, "rag")
W = max(end_a, end_b) + 64
write("RAG-enhanced-evaluation-pipelines.svg", W, 480,
      "RAG-enhanced evaluation pipelines",
      "Two lanes showing the RAG-enhanced evaluation flow for Markdown and MDX files. "
      "The file is read first, then guidelines are retrieved from the knowledge base and "
      "injected into the prompt; the model returns a parsed object via a submit_evaluation tool call.",
      lane(28, 56, W - 56, 176, "RAG-ENHANCED MARKDOWN EVALUATION PIPELINE") + "\n" + body_a + "\n" +
      lane(28, 294, W - 56, 176, "RAG-ENHANCED MDX EVALUATION PIPELINE") + "\n" + body_b)


# ── 2. Batch evaluation pipeline ─────────────────────────────────────────────
#
# Unlike the single-file pipelines this one fans out: every file is classified
# before any API call, and only the "evaluate" branch reaches the model.

W2, H2 = 1560, 560
p = [lane(28, 56, W2 - 56, H2 - 96, "BATCH EVALUATION PIPELINE (evaluate_batch.py)")]

p.append(box(64, 236, 176, 96, ["Files and folders", "passed as arguments"], "batch"))
p.append(arrow(246, 284, 292, 284))
p.append(box(296, 224, 200, 120,
             ["collect_docs()", "expands folders,", "skips node_modules", "and dot-directories"], "batch"))
p.append(arrow(502, 284, 548, 284))
p.append(box(552, 224, 200, 120,
             ["classify_documents()", "sorts every file", "before any API call"], "batch"))

# Fan-out: skip / evaluate / error
p.append('<path class="ln" d="M758 256 C806 256 806 150 850 150"/>')
p.append(arrow(758, 284, 846, 284))
p.append('<path class="ln" d="M758 312 C806 312 806 418 850 418"/>')

p.append(box(852, 110, 208, 80, ["Skip", "with a reason"], "muted"))
p.append(box(852, 244, 208, 80, ["Evaluate", "one file at a time"], "batch"))
p.append(box(852, 378, 208, 80, ["Error", "the run continues"], "muted"))

p.append(arrow(1064, 284, 1110, 284))
p.append(box(1114, 224, 200, 120,
             ["evaluate_core", "read, retrieve,", "submit_evaluation"], "batch"))
p.append(arrow(1320, 284, 1366, 284))
p.append(box(1370, 224, 160, 120,
             ["report.py", "console table,", "optional Markdown,", "exit 0 or 1"], "batch"))

# Skip reasons and the dry-run short-circuit
p.append('<text x="1076" y="140" class="s">skip-evaluation</text>')
p.append('<text x="1076" y="160" class="s">no evaluable content</text>')
p.append('<text x="1076" y="180" class="s">not an OpenAPI spec</text>')
p.append('<path class="ln" d="M652 348 V416"/>')
p.append(box(524, 420, 256, 80, ["--dry-run stops here", "lists every disposition,", "exits before any API call"], "muted"))

write("batch-evaluation-pipeline.svg", W2, H2,
      "Batch evaluation pipeline",
      "Files and folders are collected, then every file is classified as evaluate, skip, or error "
      "before any API call. Only evaluable files reach the model. Results are rendered as a console "
      "table and an optional Markdown report, with an exit code that gates scripts.",
      "\n".join(p))


# ── 3. Continuous integration pipeline ───────────────────────────────────────

W3, H3 = 1760, 330
q = [lane(28, 56, W3 - 56, H3 - 96, "CONTINUOUS INTEGRATION PIPELINE (GitHub Action)")]

ci_steps = [
    ["Pull request", "opened or updated"],
    ["Action checks out", "the branch and", "rebuilds the index"],
    ["Diff against the", "base branch for", "changed docs"],
    ["classify_documents()", "then score each", "changed file"],
    ["Sticky PR comment", "from ci_report.md"],
]
body_ci, end_ci = render_lane(64, 112, ci_steps, "ci", bw=210, bh=112, gap=48)
q.append(body_ci)
q.append(arrow(end_ci + 6, 168, end_ci + 44, 168))
q.append(box(end_ci + 48, 112, 226, 112,
             ["Check passes", "or fails on", "DOC_QUALITY_THRESHOLD"], "ci"))

write("ci-evaluation-pipeline.svg", W3, H3,
      "Continuous integration pipeline",
      "On each pull request the action rebuilds the index, diffs against the base branch, classifies "
      "and scores the changed documentation files, posts a sticky comment, and fails the check when a "
      "doc scores below the configured threshold.",
      "\n".join(q))
