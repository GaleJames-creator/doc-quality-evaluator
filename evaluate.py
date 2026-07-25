"""
evaluate.py

Baseline documentation quality evaluator.

Evaluates a documentation file against five criteria: clarity, completeness,
accuracy, consistency, and structure (Diátaxis). Returns a JSON report.

Supports both .md and .mdx files. MDX-specific syntax (frontmatter, import
statements, JSX component tags) is stripped before evaluation. Content inside
JSX components (e.g., <Note>, <Warning>) is preserved — only the tags are removed.

Usage:
    python3 evaluate.py samples/my-doc.mdx
    python3 evaluate.py samples/my-doc.md

Notes:
    - Always edit the source .mdx file first, then copy it to the samples/
      folder before running the evaluator.
    - MDX formatting is stripped automatically — the evaluation reflects
      content quality, not MDX component rendering.
"""

from dotenv import load_dotenv
import anthropic
import json
import re
import sys

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
    # Remove YAML frontmatter (--- block at the top of the file)
    content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)

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

SYSTEM_PROMPT = """
You are a documentation quality reviewer specializing in API and 
developer documentation, particularly for fintech and payments platforms.
Documentation samples may include REST API reference docs, integration 
guides, and OpenAPI specifications.

Evaluate the provided documentation against these five criteria. For each, 
give a score from 1–5 and one sentence of specific, actionable feedback.

Criteria:
1. CLARITY — Is the writing clear and free of ambiguity?
2. COMPLETENESS — Are all parameters, responses, and error codes documented?
3. ACCURACY — Are code examples syntactically correct and realistic?
4. CONSISTENCY — Is terminology, tone, and formatting consistent throughout?
   When evaluating code examples, respect language-specific naming conventions:
   - JSON field names use camelCase (e.g., `bookId`, `createdDate`) — this is
     correct API field naming and should not be flagged as inconsistent.
   - Python variable names use snake_case (e.g., `book_id`, `created_date`) —
     this is correct Python convention.
   - Differences between JSON field names and Python variable names are not
     inconsistencies — they reflect the appropriate naming convention for each
     language and context.
   Only flag naming as inconsistent when the same language uses mixed conventions
   within a single example, or when a value passed between languages is mismatched
   (e.g., a Python script serializes `book_id` as a JSON key when the API expects
   `bookId`).
5. STRUCTURE — Does the content follow the appropriate Diátaxis type 
   (tutorial / how-to / reference / explanation / overview)?

Return your response as JSON only. Do not include any explanation, 
preamble, or markdown code fences — raw JSON only, in this exact format:
{
  "clarity":      {"score": 0, "feedback": ""},
  "completeness": {"score": 0, "feedback": ""},
  "accuracy":     {"score": 0, "feedback": ""},
  "consistency":  {"score": 0, "feedback": ""},
  "structure":    {"score": 0, "feedback": ""},
  "overall":      {"score": 0, "summary": ""}
}
"""


# ── Resolve file path ────────────────────────────────────────────────────────

if len(sys.argv) < 2:
    print("Usage: python3 evaluate.py <path-to-doc>")
    print("Example: python3 evaluate.py samples/my-doc.mdx")
    sys.exit(1)

doc_path = sys.argv[1]

try:
    with open(doc_path, "r", encoding="utf-8") as f:
        raw_content = f.read()
except FileNotFoundError:
    print(f"Error: File not found — {doc_path}")
    sys.exit(1)

print(f"Evaluating: {doc_path}")


# ── Preprocess MDX if needed ─────────────────────────────────────────────────

if doc_path.endswith(".mdx"):
    doc_content = strip_mdx(raw_content)
    print("MDX syntax stripped — JSX tags removed, content preserved.")
else:
    doc_content = raw_content


# ── Call the Anthropic API ───────────────────────────────────────────────────

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

print("Calling Anthropic API...")

message = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
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