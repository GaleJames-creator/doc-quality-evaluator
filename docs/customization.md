# Customization

This page is optional. Read it only if you want to adapt the evaluator to your own documentation standards &mdash; by editing the system prompt, replacing the knowledge base, or changing which criteria the evaluator scores.

## Prerequisites

* The setup in the [repository README](../README.md) completed, and at least one successful evaluation run, so you have a baseline to compare your changes against.
* Rerun `python3 build_index.py` after any change to `knowledge_base/`. Edits to those files have no effect until the index is rebuilt.

## Customize the system prompt

The evaluation criteria, scoring scale, and doc context are all controlled by the `SYSTEM_PROMPT` variable in `evaluate.py` and `evaluate_rag.py`. Modify that string to adapt the evaluator to your own doc standards, style guide, or content types.

> **Note**: The `SYSTEM_PROMPT` is the single point of customization for the `baseline` evaluator. Change that string, and the entire evaluation changes.

Every customization follows the same pattern: find the relevant lines in `SYSTEM_PROMPT` and replace them. The following before-and-after examples show the pattern.

### Targeting a different doc domain

The opening lines of `SYSTEM_PROMPT` specify API and developer docs for fintech. A writer documenting medical devices, legal software, or end-user consumer products would update that context to get more relevant feedback.

Replace this:

```text
You are a documentation quality reviewer specializing in API and 
developer documentation, particularly for fintech and payments platforms.
```

With this:

```text
You are a documentation quality reviewer specializing in software 
documentation for medical devices, with attention to regulatory 
terminology and safety-critical instructions.
```

### Replacing the Diátaxis criterion with a style guide check

Replace this:

```text
5. STRUCTURE — Does the content follow the appropriate Diátaxis type 
   (tutorial / how-to / reference / explanation / overview)?
```

> **Note**: `evaluate.py` (baseline) already lists the same five types in its own `SYSTEM_PROMPT`. However, baseline has no way to honor a document's declared `docType`&mdash;`strip_mdx()` removes the entire frontmatter block before the content reaches the model, and there's no retrieval step to guarantee a type's checklist gets included. Baseline always infers the Diátaxis type from content alone; only `RAG-enhanced` reads and grounds against an explicit `docType`.

With this:

```text
5. STYLE GUIDE — Does the content follow the Microsoft Writing Style 
   Guide conventions for tone, voice, and terminology?
```

### Changing the scoring scale

You can change the 1&ndash;5 scale to 1&ndash;10 or a pass/fail system by updating the prompt instructions.

Replace this:

```text
Evaluate the provided documentation against these five criteria. For each, 
give a score from 1–5 and one sentence of specific, actionable feedback.
```

With this:

```text
Evaluate the provided documentation against these five criteria. For each, 
give a rating of PASS or FAIL and one sentence of specific, actionable feedback.
```

> **Note**: If you change the scoring scale, also update the JSON output format instructions in `SYSTEM_PROMPT`, so the `score` fields match the new scale.

### Adding a sixth criterion

Criteria aren't capped at five. Add a new one to `SYSTEM_PROMPT` and extend the JSON output format to match.

Replace this:

```text
5. STRUCTURE — Does the content follow the appropriate Diátaxis type 
   (tutorial / how-to / reference / explanation / overview)?

Return your response as JSON only. Do not include any explanation, preamble,
or markdown code fences — raw JSON only, in this exact format:
{
  "clarity":      {"score": 0, "feedback": ""},
  "completeness": {"score": 0, "feedback": ""},
  "accuracy":     {"score": 0, "feedback": ""},
  "consistency":  {"score": 0, "feedback": ""},
  "structure":    {"score": 0, "feedback": ""},
  "overall":      {"score": 0, "summary": ""}
}
```

With this:

```text
5. STRUCTURE — Does the content follow the appropriate Diátaxis type 
   (tutorial / how-to / reference / explanation / overview)?
6. ACCESSIBILITY — Does the content use descriptive link text, alt text 
   for images, and heading levels that don't skip (e.g., H2 to H4)?

Return your response as JSON only. Do not include any explanation, preamble,
or markdown code fences — raw JSON only, in this exact format:
{
  "clarity":       {"score": 0, "feedback": ""},
  "completeness":  {"score": 0, "feedback": ""},
  "accuracy":      {"score": 0, "feedback": ""},
  "consistency":   {"score": 0, "feedback": ""},
  "structure":     {"score": 0, "feedback": ""},
  "accessibility": {"score": 0, "feedback": ""},
  "overall":       {"score": 0, "summary": ""}
}
```

> **Important**: Make this change in both `evaluate.py` and `evaluate_rag.py` if you want the new criterion scored in both modes, and add the new field to the Output fields table in [Output reference](output-reference.md).

### Replacing completeness with a release-notes-specific criterion

Swap a criterion's focus entirely rather than adding one&mdash;useful when a doc type (like release notes) has a different definition of "complete."

Replace this:

```text
2. COMPLETENESS — Are all parameters, responses, and error codes documented?
```

With this:

```text
2. BREAKING CHANGES — Are all breaking changes clearly flagged, with 
   migration guidance provided for each one?
```

> **Note**: If you rename a criterion's label, also update the corresponding JSON key in `SYSTEM_PROMPT`'s output format instructions (e.g., `"completeness"` to `"breaking_changes"`) and the Output fields table in [Output reference](output-reference.md), so the prompt, the JSON schema, and the docs all stay in sync.

## Customize the knowledge base

The `RAG-enhanced` evaluator has a second customization point: the `knowledge_base/` folder. The evaluator retrieves guideline chunks from this folder and grounds its assessment in them, so adding your own standards changes what the evaluation is measured against. For example:

* Add your company style guide as a Markdown file.
* Add product-specific documentation standards.
* Replace `api_doc_standards.md` with standards for your own doc domain.

Structure each file with `##` headers &mdash; `build_index.py` splits files on level-2 headers, and each section becomes a separate retrievable chunk.

`build_index.py` also tags the type-defining sections across the knowledge base with metadata, matched by exact header text. The four Diátaxis type sections plus `## Overview / Index Pages` live in `diataxis_types.md`; `## Integration Guide Standards` lives in `api_doc_standards.md`.

> **Important**: If you rename or restructure these headers in `diataxis_types.md` or `api_doc_standards.md`, update `DOCTYPE_HEADERS` in `build_index.py` to match. A mismatch fails silently &mdash; retrieval falls back to similarity-only ranking for that type instead of raising an error.

```python
DOCTYPE_HEADERS = {
    "## Tutorials": "tutorial",
    "## How-to Guides": "how-to",
    "## Reference Docs": "reference",
    "## Explanation Docs": "explanation",
    "## Overview / Index Pages": "overview",
    "## Integration Guide Standards": "integration-guide",
}
```

> **Important**: Re-run `python3 build_index.py` after adding or updating knowledge base files. The vector index does not update automatically.

## Tips for writing effective prompts

* Adopt a specialized persona: Assign the AI a specific role to ensure the evaluation maintains a professional tone and focus. For example:

  ```text
  Act as a Senior Technical Writer. Evaluate the technical guide for completeness, accuracy, and clarity.
  ```

* Provide an example of a good document. For example:

  ```text
  Here's an example of a good API document. [insert example]. Evaluate the following new document using the same standards.
  ```

* Structure the output. For example:

  ```text
  Provide the evaluation in a Markdown table with these columns: Issue Type (Accuracy/Clarity), Score (0-5), Feedback/Summary.
  ```

* Specify the output format explicitly: Tell the model exactly what format to return results in and what to exclude.

  ```text
  Return your response as JSON only. Do not include explanations, 
  preambles, or Markdown code fences.
  ```

---

[Back to the doc-quality-evaluator README](../README.md)
