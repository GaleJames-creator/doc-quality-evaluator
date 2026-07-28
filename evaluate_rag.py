"""
evaluate_rag.py

RAG-enhanced documentation quality evaluator (command-line interface).

Retrieves relevant documentation guidelines from a local ChromaDB vector store,
injects them into the prompt as grounding context, and asks the model to score
the document against five criteria. The evaluation logic lives in
evaluate_core.py so it can be shared with the CI runner (ci/evaluate_changed.py).

Supports both .md and .mdx files. MDX-specific syntax (frontmatter, import
statements, JSX component tags) is stripped before evaluation; content inside
JSX components (e.g., <Note>, <Warning>) is preserved — only the tags are removed.

Prerequisites:
    1. Run build_index.py at least once to create the vector index.
    2. ANTHROPIC_API_KEY set in your .env file.

Usage:
    python3 evaluate_rag.py samples/my-doc.mdx
    python3 evaluate_rag.py samples/my-doc.md
"""

import json
import sys

from evaluate_core import (
    load_document,
    get_collection,
    retrieve_guidelines,
    format_guidelines,
    build_system_prompt,
    call_model,
    parse_result,
)


def main() -> int:
    # ── Resolve file path ────────────────────────────────────────────────────
    if len(sys.argv) < 2:
        print("Usage: python3 evaluate_rag.py <path-to-doc>")
        print("Example: python3 evaluate_rag.py samples/my-doc.mdx")
        return 1

    doc_path = sys.argv[1]

    try:
        doc_content, doc_type = load_document(doc_path)
    except FileNotFoundError:
        print(f"Error: File not found — {doc_path}")
        return 1

    print(f"Evaluating: {doc_path}" + (f"  (docType: {doc_type})" if doc_type else ""))
    if doc_path.endswith(".mdx"):
        print("MDX syntax stripped — JSX tags removed, content preserved.")

    # ── Load the vector store ────────────────────────────────────────────────
    try:
        collection = get_collection()
    except RuntimeError as exc:
        print(f"Error: {exc}")
        return 1

    # ── Retrieve relevant guidelines ─────────────────────────────────────────
    retrieved = retrieve_guidelines(collection, doc_content, doc_type)

    print(f"\nRetrieved {len(retrieved)} guideline chunk(s) from the knowledge base:")
    for _chunk, meta, dist in retrieved:
        dist_label = f"{dist:.4f}" if dist is not None else "guaranteed match"
        print(f"  - {meta['source']} chunk {meta['chunk']}  (similarity distance: {dist_label})")

    # ── Call the Anthropic API ───────────────────────────────────────────────
    system_prompt = build_system_prompt(format_guidelines(retrieved), doc_type)

    print("\nCalling Anthropic API...")
    raw = call_model(system_prompt, doc_content)

    # ── Parse and print results ──────────────────────────────────────────────
    try:
        result = parse_result(raw)
    except ValueError as exc:
        print(f"\n{exc}")
        return 1

    print("\n── Evaluation Results ──────────────────────────────────────────────────\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
