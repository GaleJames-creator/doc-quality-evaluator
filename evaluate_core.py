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
import re
import frontmatter
import yaml  # PyYAML — direct dependency for OpenAPI spec loading

load_dotenv()


# ── Configuration ────────────────────────────────────────────────────────────

CHROMA_DB_PATH  = "./chroma_db"       # must match build_index.py
COLLECTION_NAME = "doc_guidelines"
TOP_K           = 5                   # number of guideline chunks to retrieve
MODEL           = "claude-haiku-4-5-20251001"

# Criteria returned by the evaluator, in display order. "overall" is handled
# separately because its payload is {score, summary} rather than {score, feedback}.
CRITERIA = ["clarity", "completeness", "accuracy", "consistency", "structure"]


# ── Structured-output tool schema ────────────────────────────────────────────
#
# The model returns its evaluation by calling this tool rather than emitting JSON
# as text. The SDK hands back `tool_use.input` as an already-parsed dict, so there
# is no text-to-JSON step that can fail — this eliminates the class of parse errors
# caused by unescaped quotes inside feedback strings.

def _flat_properties() -> dict:
    props: dict = {}
    for c in CRITERIA:
        props[f"{c}_score"] = {
            "type": "integer", "minimum": 1, "maximum": 5,
            "description": f"{c.capitalize()} score from 1 (poor) to 5 (excellent).",
        }
        props[f"{c}_feedback"] = {
            "type": "string",
            "description": f"One sentence of specific, actionable feedback on {c}.",
        }
    props["overall_score"] = {
        "type": "number", "minimum": 1, "maximum": 5,
        "description": "Overall quality score from 1 to 5.",
    }
    props["overall_summary"] = {
        "type": "string",
        "description": "A short overall summary of the evaluation.",
    }
    return props


# The schema is intentionally FLAT (top-level scalar fields, no nested objects).
# Small models fill flat integer/string fields far more reliably than nested
# {score, feedback} objects — Haiku frequently mangled the nested inner fields,
# leaking tool-call syntax into the values. score_document reassembles these flat
# fields into the nested {criterion: {score, feedback}} shape the rest of the code
# expects, so callers are unaffected.
RESULT_TOOL = {
    "name": "submit_evaluation",
    "description": "Submit the documentation quality score and feedback for each criterion.",
    "input_schema": {
        "type": "object",
        "properties": _flat_properties(),
        "required": (
            [f"{c}_score" for c in CRITERIA]
            + [f"{c}_feedback" for c in CRITERIA]
            + ["overall_score", "overall_summary"]
        ),
    },
}


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

YAML_EXTS = (".yaml", ".yml")


def is_openapi_path(doc_path: str) -> bool:
    """Return True if the path is a YAML file (evaluated as an OpenAPI spec)."""
    return doc_path.endswith(YAML_EXTS)


def _load_yaml_spec(doc_path: str):
    """
    Load a YAML file for evaluation, returning (doc_content, doc_type).

    The raw YAML text is what gets evaluated (so feedback can reference the
    actual `summary`, `description`, and example fields the writer sees), but
    the file is parsed first to fail fast on invalid YAML and to confirm it is
    an OpenAPI/Swagger spec. Specs are graded as docType `reference` — the
    Diátaxis type whose checklist covers parameters, responses, and error codes.

    Raises ValueError if the file is not parseable YAML or has no
    `openapi`/`swagger` version key.
    """
    with open(doc_path, encoding="utf-8") as f:
        raw = f.read()

    try:
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ValueError(f"Not parseable YAML: {exc}") from exc

    if not isinstance(parsed, dict) or not ({"openapi", "swagger"} & parsed.keys()):
        raise ValueError(
            "YAML file has no `openapi` or `swagger` key — only OpenAPI/Swagger "
            "specs are supported for YAML evaluation."
        )

    return raw, "reference"


def load_document(doc_path: str):
    """
    Load a .md, .mdx, .yaml, or .yml file, returning (doc_content, doc_type).

    For Markdown/MDX, doc_type comes from the frontmatter `docType` field (or
    None). MDX files are run through strip_mdx so the evaluation reflects
    content quality rather than JSX rendering. YAML files must be OpenAPI/
    Swagger specs and are evaluated as docType `reference` (see _load_yaml_spec).

    Raises FileNotFoundError if the path does not exist.
    """
    if is_openapi_path(doc_path):
        return _load_yaml_spec(doc_path)

    post = frontmatter.load(doc_path)
    doc_type = post.metadata.get("docType")

    if doc_path.endswith(".mdx"):
        content = strip_mdx(post.content)
    else:
        content = post.content

    return content, doc_type


def is_evaluation_skipped(doc_path: str) -> bool:
    """
    Return True if the document opts out of evaluation via frontmatter.

    A doc is skipped when its frontmatter sets `skip-evaluation: true`. This lets
    non-API pages — portfolio overviews, process memos, changelogs — avoid being
    graded against the API-reference rubric (and wrongly failing the CI gate).
    Honored by the CI and batch runners; the interactive CLI evaluates whatever
    file it is explicitly given. YAML specs have no frontmatter and are never
    skipped (frontmatter.load could misread a spec's leading `---` document
    separator as a frontmatter fence, so they are excluded before parsing).
    """
    if is_openapi_path(doc_path):
        return False
    try:
        value = frontmatter.load(doc_path).metadata.get("skip-evaluation")
    except FileNotFoundError:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return bool(value)


def classify_documents(paths: list[str], discovered_yaml=None):
    """
    Partition doc paths into (to_evaluate, skipped, errors) without calling
    the API or opening the vector store.

    skipped is a list of (path, reason) tuples; errors is (path, message).
    A file is skipped for "skip-evaluation" frontmatter or for having no
    evaluable content — e.g., a Mintlify spec-driven page whose body is only
    frontmatter and component references, which strips to nothing. Sending
    such a file to the model wastes a call and returns a confusing 400 error;
    an intentionally content-free page is not a quality defect, so it does
    not fail the gate.

    discovered_yaml holds YAML paths found by folder recursion rather than
    named by the caller. Docs repos routinely contain configuration YAML
    (linter rulesets, CI workflows), so a discovered YAML that isn't an
    OpenAPI spec is treated as "not a doc" and skipped rather than errored.
    An explicitly named non-spec YAML still errors — the caller asked for
    that file, so silently skipping it would hide a mistake. Other load
    failures land in errors, which do fail the gate.
    """
    discovered_yaml = set(discovered_yaml or ())
    to_evaluate, skipped, errors = [], [], []
    for path in paths:
        if is_evaluation_skipped(path):
            skipped.append((path, "skip-evaluation"))
            continue
        try:
            content, _ = load_document(path)
        except ValueError as exc:
            if path in discovered_yaml:
                skipped.append((path, "not an OpenAPI spec"))
            else:
                errors.append((path, str(exc).splitlines()[0]))
            continue
        except Exception as exc:  # noqa: BLE001 — classify any failure per-file
            errors.append((path, str(exc).splitlines()[0]))
            continue
        if not content.strip():
            skipped.append((path, "no evaluable content"))
            continue
        to_evaluate.append(path)
    return to_evaluate, skipped, errors


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

def build_system_prompt(formatted_guidelines: str, doc_type, is_openapi: bool = False) -> str:
    """Build the RAG-enhanced system prompt for the given docType."""
    if is_openapi:
        type_line = (
            "The document is an OpenAPI (Swagger) specification in YAML, "
            "evaluated as `docType: reference`. Grade the human-readable "
            "content — `summary`, `description`, parameter and response "
            "documentation, and examples — against the API reference "
            "standards. Do not penalize Structure for YAML's spec-mandated "
            "layout (`paths`, `components`, and so on); assess whether every "
            "operation documents its parameters, responses, and error codes. "
            "Do not re-classify the document yourself."
        )
    elif doc_type == "integration-guide":
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

Provide your assessment by calling the `submit_evaluation` tool. For each of the
five criteria, give an integer score from 1–5 and one sentence of specific,
actionable feedback; also give an overall score and a short summary. Respond only
through the tool — do not write any prose in your reply.
"""


# ── Model call (structured output) ───────────────────────────────────────────

def _clean_score_text(score, text):
    """
    Normalize a (score, text) pair from the flat tool output.

    The score should be numeric, but the model occasionally misfiles the feedback
    sentence into the score field (leaving the text field empty). When the score
    isn't a number, recover it as the text so nothing is lost and the score column
    stays clean.
    """
    text = str(text or "").strip()
    if isinstance(score, bool):          # bool is a subclass of int — treat as invalid
        return None, text
    if isinstance(score, (int, float)):
        return score, text
    if isinstance(score, str):
        s = score.strip()
        try:
            return (float(s) if s else None), text
        except ValueError:
            return None, (text or s)     # non-numeric string in the score field → recover as text
    return None, text


def _nest_result(flat: dict) -> dict:
    """Reassemble the flat tool fields into the nested shape, tolerating misfiled fields."""
    result = {}
    for c in CRITERIA:
        score, feedback = _clean_score_text(flat.get(f"{c}_score"), flat.get(f"{c}_feedback", ""))
        result[c] = {"score": score, "feedback": feedback}
    score, summary = _clean_score_text(flat.get("overall_score"), flat.get("overall_summary", ""))
    result["overall"] = {"score": score, "summary": summary}
    return result


def score_document(system_prompt: str, doc_content: str, model: str = MODEL) -> dict:
    """
    Call the model with a forced tool call and return the structured result dict.

    The evaluation comes back as `tool_use.input` — already parsed by the SDK — so
    there is no JSON-in-text step to fail (which fixed the earlier unescaped-quote
    parse errors). The tool schema is flat; this reassembles it into the nested
    {criterion: {score, feedback}} shape the rest of the code expects.
    """
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system_prompt,
        tools=[RESULT_TOOL],
        tool_choice={"type": "tool", "name": RESULT_TOOL["name"]},
        messages=[{"role": "user", "content": doc_content}],
    )
    for block in message.content:
        if getattr(block, "type", None) == "tool_use" and block.name == RESULT_TOOL["name"]:
            return _nest_result(dict(block.input))
    raise ValueError("Model did not return a submit_evaluation tool call.")


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
    system_prompt = build_system_prompt(
        format_guidelines(retrieved), doc_type, is_openapi=is_openapi_path(doc_path)
    )
    return score_document(system_prompt, content)
