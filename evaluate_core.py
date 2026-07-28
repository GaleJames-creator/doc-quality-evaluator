"""
evaluate_core.py

Reusable core for the RAG-enhanced documentation quality evaluator.

This module holds the evaluation logic as importable functions so it can be
driven two ways:

  * evaluate_rag.py — the interactive CLI (`python3 evaluate_rag.py <doc>`)
  * ci/evaluate_changed.py — the GitHub Actions runner that scores changed
    docs on a pull request

Importing this module has no side effects beyond loading environment variables
(so a local `.env` continues to work); it does not open the database or call
the API until you invoke a function.

Prerequisites:
    1. Run build_index.py at least once to create the vector index.
    2. ANTHROPIC_API_KEY available in the environment (via .env locally, or a
       repository secret in CI).
"""

from dotenv import load_dotenv
import anthropic
import chromadb
import json
import re
import frontmatter

load_dotenv()


# ── Configuration ────────────────────────────────────────────────────────────

CHROMA_DB_PATH  = "./chroma_db"       # must match build_index.py
COLLECTION_NAME = "doc_guidelines"
TOP_K           = 5                   # number of guideline chunks to retrieve
MODEL           = "claude-haiku-4-5-20251001"

# Criteria returned by the evaluator, in display order. "overall" is handled
# separately because its payload is {score, summary} rather than {score, feedback}.
CRITERIA = ["clarity", "completeness", "accuracy", "consistency", "structure"]


# ── MDX preprocessing ────────────────────────────────────────────────────────

def strip_mdx(content: str) -> str:
    """
    Remove MDX-specific syntax from a file before evaluation.

    Strips YAML frontmatter is handled by the frontmatter loader; here we strip
    import statements and JSX component tags while preserving all text content,
    including text inside JSX components, standard Markdown, and code blocks.
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


# ── Load a document ──────────────────────────────────────────────────────────

def load_document(doc_path: str):
    """
    Load a .md or .mdx file, returning (doc_content, doc_type).

    doc_type comes from the frontmatter `docType` field (or None). MDX files
    are run through strip_mdx so the evaluation reflects content quality rather
    than JSX rendering.

    Raises FileNotFoundError if the path does not exist.
    """
    post = frontmatter.load(doc_path)
    doc_type = post.metadata.get("docType")

    if doc_path.endswith(".mdx"):
        content = strip_mdx(post.content)
    else:
        content = post.content

    return content, doc_type


# ── Vector store ─────────────────────────────────────────────────────────────

def get_collection(chroma_path: str = CHROMA_DB_PATH, name: str = COLLECTION_NAME):
    """
    Open the persistent ChromaDB collection built by build_index.py.

    Raises RuntimeError with an actionable message if the collection is missing.
    """
    client = chromadb.PersistentClient(path=chroma_path)
    try:
        return client.get_collection(name=name)
    except Exception as exc:
        raise RuntimeError(
            f"Collection '{name}' not found at '{chroma_path}'. "
            "Run build_index.py first to create the vector index."
        ) from exc


def retrieve_guidelines(collection, doc_content: str, doc_type, top_k: int = TOP_K):
    """
    Retrieve the most relevant guideline chunks for a document.

    Returns a list of (chunk_text, metadata, distance) tuples. Distance is None
    for chunks that were added as a guaranteed docType match rather than by
    semantic similarity (lower distance = more similar).
    """
    # Use the first 2,000 characters as the query. This captures the doc type,
    # subject, and key terms without diluting the signal with the whole doc.
    query_text = doc_content[:2000]

    results = collection.query(query_texts=[query_text], n_results=top_k)

    retrieved_chunks    = list(results["documents"][0])
    retrieved_sources   = list(results["metadatas"][0])
    retrieved_distances = list(results["distances"][0])

    # Guarantee the declared docType's own checklist is included, regardless of
    # how semantic similarity ranks it. Without this, a page whose content reads
    # like a different type can retrieve that other type's chunk instead of its own.
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
                    retrieved_distances.append(None)  # guaranteed, not similarity-ranked
                    retrieved_ids.append(chunk_id)

    return list(zip(retrieved_chunks, retrieved_sources, retrieved_distances))


def format_guidelines(retrieved) -> str:
    """Format retrieved (chunk, meta, distance) tuples for the system prompt."""
    formatted = ""
    for i, (chunk, meta, _distance) in enumerate(retrieved, start=1):
        formatted += f"\n### Guideline {i} (from {meta['source']})\n{chunk}\n"
    return formatted


# ── Prompt construction ──────────────────────────────────────────────────────

def build_system_prompt(formatted_guidelines: str, doc_type) -> str:
    """Build the RAG-enhanced system prompt for the given docType."""
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

    return f"""
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


# ── Model call and parsing ───────────────────────────────────────────────────

def call_model(system_prompt: str, doc_content: str, model: str = MODEL) -> str:
    """Call the Anthropic API and return the raw response text."""
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": doc_content}],
    )
    return message.content[0].text


def parse_result(raw: str) -> dict:
    """
    Parse the model's raw response into a result dict.

    Tolerates markdown code fences and surrounding text. Raises ValueError if no
    valid JSON object can be recovered.
    """
    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    raise ValueError(f"Could not parse a JSON object from the model response:\n{raw}")


# ── Convenience entry point ──────────────────────────────────────────────────

def evaluate_document(doc_path: str, collection=None, top_k: int = TOP_K) -> dict:
    """
    Evaluate a single document end to end and return the result dict.

    Pass an existing `collection` to reuse one vector-store handle across many
    files (as the CI runner does); otherwise one is opened for this call.

    The returned dict matches the prompt schema: a {score, feedback} entry for
    each of CRITERIA, plus an {score, summary} "overall" entry.
    """
    content, doc_type = load_document(doc_path)
    if collection is None:
        collection = get_collection()
    retrieved = retrieve_guidelines(collection, content, doc_type, top_k)
    system_prompt = build_system_prompt(format_guidelines(retrieved), doc_type)
    raw = call_model(system_prompt, content)
    return parse_result(raw)
