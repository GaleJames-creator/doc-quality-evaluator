from dotenv import load_dotenv
import os
import anthropic
import json

load_dotenv()

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
5. STRUCTURE — Does the content follow the appropriate Diátaxis type 
   (tutorial / how-to / reference / explanation)?

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

# Read a doc file
with open("webhooks-Admin-UI.md", "r") as f:
    doc_content = f.read()

# Call the API
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

message = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    system=SYSTEM_PROMPT,   # the evaluation prompt above
    messages=[
        {"role": "user", "content": doc_content}
    ]
)

# Parse and print results
raw = message.content[0].text
clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
result = json.loads(clean)
print(json.dumps(result, indent=2))