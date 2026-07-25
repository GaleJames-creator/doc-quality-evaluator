"""
evaluate_rag.py

RAG-enhanced documentation quality evaluator.

Extends evaluate.py by retrieving relevant documentation guidelines from a
local ChromaDB vector store before calling the Anthropic API. The retrieved
guidelines are injected into the prompt as grounding context, making the
evaluation more specific and consistent with your documented standards.

Supports both .md and .mdx files. MDX-specific syntax (frontmatter, import
statements, JSX component tags) is stripped before evaluation. Content inside
JSX components (e.g., <Note>, <Warning>) is preserved — only the tags are removed.

Prerequisites:
    1. Run build_index.py at least once to create the vector index.
    2. ANTHROPIC_API_KEY set in your .env file.

Usage:
    python3 evaluate_rag.py samples/my-doc.mdx
    python3 evaluate_rag.py samples/my-doc.md

Notes:
    - Always edit the source .mdx file first, then copy it to the samples/
      folder before running the evaluator.
    - MDX formatting is stripped automatically — the evaluation reflects
      content quality, not MDX component rendering.
"""

from dotenv import load_dotenv
import anthropic
import chromadb
import json
import re
import sys
import frontmatter

load_dotenv()


# ── MDX preprocessing ────────────────────────────────────────────────────────

def strip_mdx(content: str) -> str:
    """
    Remove MDX-specific syntax from a file before evaluation.

    Strips:
    - YAML frontmatter (--- ... ---)
    - import statements
    - JSX component opening and closing tags (e.g., <Note>, </Note>)

    Preserves:
    - All text content, including text inside JSX components
    - Standard Markdown formatting
    - Code blocks
    """

    # Remove import statements (e.g., import X from 'y')
    content = re.sub(r'^import\s+.+\n', '', content, flags=re.MULTILINE)

    # Remove JSX self-closing tags (e.g., <Prerequisites />)
    content = re.sub(r'<[A-Z][A-Za-z]*[^>]*/>', '', content)

    # Remove JSX opening tags (e.g., <Note>, <CodeGroup language="python">)
    content = re.sub(r'<[A-Z][A-Za-z]*[^>]*>', '', content)

    # Remove JSX closing tags (e.g., </Note>, </CodeGroup>)
    content = re.sub(r'</[A-Z][A-Za-z]*>', '', content)

    # Remove MDX expression blocks (e.g., {/* comment */})
    content = re.sub(r'\{/\*.*?\*/\}', '', content, flags=re.DOTALL)

    # Collapse multiple blank lines left by removed tags into a single blank line
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content.strip()


# ── Configuration ────────────────────────────────────────────────────────────

CHROMA_DB_PATH  = "./chroma_db"       # must match build_index.py
COLLECTION_NAME = "doc_guidelines"
TOP_K           = 5                   # number of guideline chunks to retrieve


# ── Resolve file path ────────────────────────────────────────────────────────

if len(sys.argv) < 2:
    print("Usage: python3 evaluate_rag.py <path-to-doc>")
    print("Example: python3 evaluate_rag.py samples/my-doc.mdx")
    sys.exit(1)

doc_path = sys.argv[1]

try:
    post = frontmatter.load(doc_path)
except FileNotFoundError:
    print(f"Error: File not found — {doc_path}")
    sys.exit(1)

doc_type = post.metadata.get("docType")
print(f"Evaluating: {doc_path}" + (f"  (docType: {doc_type})" if doc_type else ""))


# ── Preprocess MDX if needed ─────────────────────────────────────────────────

if doc_path.endswith(".mdx"):
    doc_content = strip_mdx(post.content)
    print("MDX syntax stripped — JSX tags removed, content preserved.")
else:
    doc_content = post.content


# ── Load the vector store ────────────────────────────────────────────────────

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

try:
    collection = chroma_client.get_collection(name=COLLECTION_NAME)
except Exception:
    print(f"Error: Collection '{COLLECTION_NAME}' not found.")
    print("Run build_index.py first to create the vector index.")
    sys.exit(1)


# ── Retrieve relevant guidelines ─────────────────────────────────────────────

# Use the first 2,000 characters of the doc as the query.
# This captures the doc type, subject, and key terms — enough for semantic search.
# Using the full doc can dilute the query signal.

query_text = doc_content[:2000]

results = collection.query(
    query_texts=[query_text],
    n_results=TOP_K,
)

retrieved_chunks    = results["documents"][0]   # list of matching text chunks
retrieved_sources   = results["metadatas"][0]   # list of source file metadata
retrieved_distances = results["distances"][0]   # lower = more similar

# Guarantee the declared docType's own checklist is included, regardless of
# how semantic similarity ranks it. Without this, a page whose content reads
# like a different type (e.g., an overview page listing endpoints) can
# retrieve that other type's chunk instead of its own.
if doc_type:
    guarantee_types = [doc_type]
    if doc_type == "integration-guide":
        guarantee_types.append("how-to")
    retrieved_ids = [f"{m['source']}_{m['chunk']}" for m in retrieved_sources]
    for gt in guarantee_types:
        type_match = collection.get(where={"applies_to_doctype": gt})
        for chunk_id, chunk, meta in zip(
            type_match["ids"], type_match["documents"], type_match["metadatas"]
        ):
            if chunk_id not in retrieved_ids:
                retrieved_chunks.append(chunk)
                retrieved_sources.append(meta)
                retrieved_distances.append(None)  # guaranteed match, not similarity-ranked
                retrieved_ids.append(chunk_id)
# Format retrieved chunks for the prompt.
# Including the source file helps the model understand which standard applies.
formatted_guidelines = ""
for i, (chunk, meta, distance) in enumerate(
    zip(retrieved_chunks, retrieved_sources, retrieved_distances), start=1
):
    formatted_guidelines += f"\n### Guideline {i} (from {meta['source']})\n{chunk}\n"

print(f"\nRetrieved {len(retrieved_chunks)} guideline chunk(s) from the knowledge base:")
for meta, dist in zip(retrieved_sources, retrieved_distances):
    dist_label = f"{dist:.4f}" if dist is not None else "guaranteed match"
    print(f"  - {meta['source']} chunk {meta['chunk']}  (similarity distance: {dist_label})")


# ── Build the RAG-enhanced system prompt ─────────────────────────────────────

if doc_type == "integration-guide":
    type_line = (
        "This document's frontmatter declares `docType: integration-guide` — "
        "a how-to guide that walks through implementing a feature. Score "
        "Structure against the How-to Guide requirements (numbered steps, "
        "prerequisites, a response section). Score Completeness against "
        "the Integration Guide Standards as well, including error-handling "
        "guidance for common failures. Do not re-classify the document yourself."
    )
elif doc_type:
    type_line = (
        f"This document's frontmatter declares `docType: {doc_type}`. "
        f"Apply only the structural requirements for that type — do not "
        f"re-classify the document yourself."
    )
else:
    type_line = (
        "This document has no `docType` declared. Infer the closest matching "
        "type from content before applying structural requirements."
    )
SYSTEM_PROMPT = f"""
You are a documentation quality reviewer specializing in API and developer
documentation, particularly for fintech and payments platforms.

The following documentation guidelines have been retrieved as relevant to the
document you are evaluating. Apply them when assessing each criterion.

<guidelines>
{formatted_guidelines}
</guidelines>

{type_line}
Evaluate the provided documentation against these five criteria. For each,
give a score from 1–5 and one sentence of specific, actionable feedback that
references the standards above where applicable.

Criteria:
1. CLARITY — Is the writing clear and free of ambiguity?
2. COMPLETENESS — Are all parameters, responses, and error codes documented?
3. ACCURACY — Are code examples syntactically correct and realistic?
4. CONSISTENCY — Is terminology, tone, and formatting consistent throughout?
   When evaluating code examples, respect language-specific naming conventions:
   - JSON field names use camelCase (e.g., `bookId`, `createdDate`) — correct
     API field naming; do not flag as inconsistent.
   - Python variable names use snake_case (e.g., `book_id`, `created_date`) —
     correct Python convention.
   - Differences between JSON field names and Python variable names are not
     inconsistencies — they reflect the appropriate convention for each language.
   Only flag naming as inconsistent when the same language uses mixed conventions
   within a single example, or when a value passed between languages is mismatched.
5. STRUCTURE — Does the content follow the appropriate Diátaxis type
   (tutorial / how-to / reference / explanation / overview)?

Return your response as JSON only. Do not include any explanation, preamble,
or markdown code fences — raw JSON only, in this exact format:
{{
  "clarity":      {{"score": 0, "feedback": ""}},
  "completeness": {{"score": 0, "feedback": ""}},
  "accuracy":     {{"score": 0, "feedback": ""}},
  "consistency":  {{"score": 0, "feedback": ""}},
  "structure":    {{"score": 0, "feedback": ""}},
  "overall":      {{"score": 0, "summary": ""}}
}}
"""


# ── Call the Anthropic API ───────────────────────────────────────────────────

client = anthropic.Anthropic()

print("\nCalling Anthropic API...")

message = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=2048,
    system=SYSTEM_PROMPT,
    messages=[
        {"role": "user", "content": doc_content}
    ]
)


# ── Parse and print results ──────────────────────────────────────────────────

raw   = message.content[0].text
clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

# Replace unescaped inner double quotes within string values
# by using a JSON repair approach
try:
    result = json.loads(clean)
except json.JSONDecodeError as e:
    # Try extracting just the JSON object if there's surrounding text
    match = re.search(r'\{.*\}', clean, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
        except json.JSONDecodeError:
            print(f"\nJSON parse error: {e}")
            print(f"\nRaw response:\n{raw}")
            sys.exit(1)
    else:
        print(f"\nJSON parse error: {e}")
        print(f"\nRaw response:\n{raw}")
        sys.exit(1)

print("\n── Evaluation Results ──────────────────────────────────────────────────\n")
print(json.dumps(result, indent=2, ensure_ascii=False))    
