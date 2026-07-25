"""
build_index.py

Indexes the knowledge_base/ folder into a local ChromaDB vector store.
Run this once before using evaluate_rag.py, and re-run any time you update
the knowledge base files.

Usage:
    python3 build_index.py

Output:
    A persistent ChromaDB database in ./chroma_db/
    Console output showing how many chunks were indexed.
"""

import chromadb
import glob
import os

# ── Configuration ───────────────────────────────────────────────────────────

KNOWLEDGE_BASE_DIR = "knowledge_base"   # folder containing .md guideline files
CHROMA_DB_PATH     = "./chroma_db"      # where ChromaDB stores the index on disk
COLLECTION_NAME    = "doc_guidelines"   # name for the vector collection


# ── Connect to ChromaDB ─────────────────────────────────────────────────────

# PersistentClient saves the index to disk so you don't rebuild every run.
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Delete and recreate the collection so re-runs start clean.
try:
    client.delete_collection(COLLECTION_NAME)
    print(f"Deleted existing '{COLLECTION_NAME}' collection.")
except Exception:
    pass  # Collection didn't exist yet — that's fine.

collection = client.create_collection(name=COLLECTION_NAME)
print(f"Created collection '{COLLECTION_NAME}'.")

# Section headers in diataxis_types.md that define a specific docType's
# structural requirements. Tagging these lets evaluate_rag.py guarantee the
# declared docType's own checklist is retrieved, regardless of how semantic
# similarity ranks it against the page being evaluated.
DOCTYPE_HEADERS = {
    "## Tutorials": "tutorial",
    "## How-to Guides": "how-to",
    "## Reference Docs": "reference",
    "## Explanation Docs": "explanation",
    "## Overview / Index Pages": "overview",
    "## Integration Guide Standards": "integration-guide",
}


# ── Load and chunk knowledge base files ─────────────────────────────────────

# Each markdown file is split on "## " headers into sections.
# Each section becomes a separate chunk in the vector store.
# Smaller chunks = more precise retrieval.

documents = []
ids       = []
metadatas = []

md_files = sorted(glob.glob(os.path.join(KNOWLEDGE_BASE_DIR, "*.md")))

if not md_files:
    print(f"\nNo .md files found in '{KNOWLEDGE_BASE_DIR}/'. Nothing to index.")
    exit(1)

for filepath in md_files:
    filename = os.path.basename(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split on level-2 headers to get meaningful sections.
    # Keep the first section (before the first ##) as a chunk too.
    raw_sections = content.split("\n## ")
    sections = [raw_sections[0].strip()]                          # intro / H1 section
    sections += ["## " + s.strip() for s in raw_sections[1:]]    # H2 sections

    for i, section in enumerate(sections):
        if not section.strip():
            continue
        applies_to_doctype = DOCTYPE_HEADERS.get(section.splitlines()[0].strip(), "")
        chunk_id = f"{filename}_{i}"
        documents.append(section)
        ids.append(chunk_id)
        metadatas.append({"source": filename, "chunk": i, "applies_to_doctype": applies_to_doctype})

print(f"\nFound {len(md_files)} file(s) → {len(documents)} chunks to index.")


# ── Add to ChromaDB ─────────────────────────────────────────────────────────

# ChromaDB uses its built-in embedding model (ONNX MiniLM) by default.
# The first run downloads the model (~30MB) automatically.
# No API key or external service required.

print("Generating embeddings and indexing... (first run may download the embedding model)")

collection.add(
    documents=documents,
    ids=ids,
    metadatas=metadatas,
)

print(f"\nDone. Indexed {len(documents)} chunks into '{CHROMA_DB_PATH}'.")
print("You can now run evaluate_rag.py.")
