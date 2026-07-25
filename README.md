# Doc quality evaluator

The `doc-quality-evaluator` (evaluator) uses Python and the Anthropic API to assess doc quality quickly. It streamlines reviews while leaving final judgment to editors. It provides two evaluation modes: `baseline` and `RAG-enhanced`.

## `Baseline` evaluation

The `evaluate.py` script uses Python and the Anthropic API to score documentation using a structured system prompt quickly.

All doc samples in the [portfolio](https://github.com/GaleJames-creator/gale-james) were evaluated using this tool before publishing.

## `RAG-enhanced` evaluation

The `evaluate_rag.py` script uses Python with RAG enhancement to score documentation against structured criteria grounded in a local knowledge base. RAG (retrieval-augmented generation) is a technique that grounds AI responses in your own reference material instead of relying only on the model's general training. The evaluator indexes your documentation standards in ChromaDB &mdash; a local vector store, meaning a database that indexes text by meaning rather than keywords &mdash; retrieves the guidelines most relevant to the doc being evaluated, and injects them into the evaluation prompt.

All doc samples in the [Mintlify portfolio](https://galejames.mintlify.app) were evaluated using this tool before publishing.

## How it works

The `doc-quality-evaluator` automates doc workflows with AI as a force multiplier, letting you keep editorial control.

### How `baseline` evaluation works

The following image shows the `baseline` evaluation flow for Markdown and MDX.

![`Baseline` evaluation pipeline](./images/baseline-evaluation-pipeline.png)

### How `RAG-enhanced` evaluation works

The following image shows the `RAG-enhanced` evaluation flow for Markdown and MDX.

![`RAG-enhanced` evaluation pipeline](./images/RAG-enhanced-evaluation-pipelines.png)

### Status messages

The `doc-quality-evaluator` prints status messages before the JSON results. If you pipe the output to a file (`python3 evaluate.py samples/doc.mdx > report.json`), the status messages will be mixed in with the JSON. You have two choices:

* If clean piped output matters for your workflow, the conventional fix is to send status messages to `stderr` and reserve `stdout` for the JSON &mdash; a one-line change (`print(..., file=sys.stderr)`) that keeps piped output clean.
* Copy the JSON from below the divider line to a report file.

A `baseline` evaluation for a Markdown file (for example, `webhooks-Admin-UI.md`) begins with the following status messages:

```text
Evaluating: samples/webhooks-Admin-UI.md
Calling Anthropic API...

── Evaluation Results ──────────────────────────────────────────────────
```

A `RAG-enhanced` evaluation for a Markdown file (for example, `webhooks-Admin-UI.md`) begins with:

```text
Evaluating: samples/webhooks-Admin-UI.md

Retrieved 5 guideline chunk(s) from the knowledge base:
  - diataxis_types.md chunk 2  (similarity distance: 1.3136)
  - diataxis_types.md chunk 3  (similarity distance: 1.5654)
  - api_doc_standards.md chunk 5  (similarity distance: 1.5762)
  - api_doc_standards.md chunk 3  (similarity distance: 1.6455)
  - api_doc_standards.md chunk 1  (similarity distance: 1.6975)

Calling Anthropic API...

── Evaluation Results ──────────────────────────────────────────────────
```

A `baseline` evaluation for an MDX file (for example, `quickstart.mdx`) begins with:

> **Note**: The `doc-quality-evaluator` strips JSX tags from MDX files, while preserving the content.

```text
Evaluating: samples/quickstart.mdx
MDX syntax stripped — JSX tags removed, content preserved.
Calling Anthropic API...

── Evaluation Results ──────────────────────────────────────────────────
```

A `RAG-enhanced` evaluation for an MDX file (for example, `quickstart.mdx`) begins with:

```text
Evaluating: samples/quickstart.mdx
MDX syntax stripped — JSX tags removed, content preserved.

Retrieved 5 guideline chunk(s) from the knowledge base:
  - api_doc_standards.md chunk 2  (similarity distance: 1.1515)
  - api_doc_standards.md chunk 1  (similarity distance: 1.1603)
  - api_doc_standards.md chunk 3  (similarity distance: 1.2346)
  - diataxis_types.md chunk 2  (similarity distance: 1.2949)
  - diataxis_types.md chunk 3  (similarity distance: 1.3859)

Calling Anthropic API...

── Evaluation Results ──────────────────────────────────────────────────
```

### Retrieval diagnostics

A `RAG-enhanced` evaluation includes retrieval diagnostics (also called a retrieval trace). It shows which knowledge-base chunks the document matched and their similarity distances so that you can verify the retrieval step is pulling the relevant guidelines.

```text
Retrieved 5 guideline chunk(s) from the knowledge base:
  - api_doc_standards.md chunk 2  (similarity distance: 1.1515)
  - api_doc_standards.md chunk 1  (similarity distance: 1.1603)
  - api_doc_standards.md chunk 3  (similarity distance: 1.2346)
  - diataxis_types.md chunk 2  (similarity distance: 1.2949)
  - diataxis_types.md chunk 3  (similarity distance: 1.3859)
```

When a document declares `docType` (see [Classifying documents with `docType`](#classifying-documents-with-doctype)), the evaluator guarantees that type's own guideline chunk is included, regardless of similarity ranking. It appears in the trace with a `guaranteed match` in place of a numeric distance:

```text
Retrieved 6 guideline chunk(s) from the knowledge base:
  - api_doc_standards.md chunk 3  (similarity distance: 1.1213)
  - api_doc_standards.md chunk 4  (similarity distance: 1.1216)
  - api_doc_standards.md chunk 1  (similarity distance: 1.1740)
  - diataxis_types.md chunk 3  (similarity distance: 1.2341)
  - api_doc_standards.md chunk 0  (similarity distance: 1.2515)
  - diataxis_types.md chunk 6  (similarity distance: guaranteed match)
```

### Scoring

The `doc-quality-evaluator` scores a Markdown or MDX doc on five criteria and returns structured JSON feedback.

* **Clarity**: Is the writing clear and free of ambiguity?
* **Completeness**: Are all parameters, responses, and error codes documented?
* **Accuracy**: Are code examples syntactically correct and realistic?
* **Consistency**: Are the terminology, tone, and formatting consistent throughout?
* **Structure**: Does the content follow the appropriate Diátaxis type (tutorial / how-to / reference / explanation / overview)?

Scores range from 1 (lowest) to 5 (highest). The evaluator provides clear feedback to improve your doc. If you see a 0, check your input file.

### JSON output format

Here's an example of the JSON output format:

```json
{
  "clarity": {
    "score": 4,
    "feedback": "..."
  },
  ...
}
```

### JSON evaluation results

The `baseline` and `RAG-enhanced` evaluators return status messages and evaluation results.

The evaluation results are in raw JSON. They do not include any explanations, preambles, or Markdown code fences. For example, when the evaluator reviewed this README, it provided the following feedback:

```text
All major setup steps and output fields are documented, but the customization section lacks concrete examples of what the modified SYSTEM_PROMPT should look like for the suggested use cases.
```

You can see the response to this Diátaxis criterion feedback. If you prefer a style guide check, see [Replacing the Diátaxis criterion with a style guide check](#replacing-the-diátaxis-criterion-with-a-style-guide-check).

See [Comparing `baseline` and `RAG-enhanced` JSON results](#comparing-baseline-and-rag-enhanced-json-results) for additional details.

See [RAG_enhanced_webhooks_admin_ui_md_sample.json](./json_samples/RAG_enhanced_webhooks_admin_ui_md_sample.json) and [RAG_enhanced_quickstart_mdx_sample.json](./json_samples/RAG_enhanced_quickstart_mdx_sample.json) for examples of the JSON results.

After you update the Markdown doc based on the evaluator's feedback, run the evaluation again. You should see the scores and evaluations improve.

### Comparing `baseline` and `RAG-enhanced` JSON results

Both evaluators were run against the same document — this README — and the results are more useful as a lesson in reading evaluator output critically than as a "RAG always wins" demonstration. The [baseline_readme_md_sample.txt](./txt_samples/baseline_readme_md_sample.txt) file shows the `baseline` result, [RAG_enhanced_readme_md_sample.txt](./txt_samples/RAG_enhanced_readme_md_sample.txt) shows the `RAG-enhanced` result including its retrieval trace, and [sample_comparison_report.txt](./txt_samples/sample_comparison_report.txt) shows the combined side-by-side comparison with additional analysis, without you having to run either script.

The headline of this run: neither evaluator returned a perfect score, and the two mostly agreed. Baseline scored clarity 4, completeness 4, accuracy 5, consistency 5, structure 5. RAG-enhanced matched on the first four and scored structure one point lower — for a reason worth noting: its Structure feedback is grounded in the classification framework itself ("this document functions primarily as a how-to guide... the Roadmap section doesn't fit the how-to-guide task orientation"), while baseline's perfect Structure score offers no standard to check it against. That traceability, not the raw score, is what RAG grounding actually adds here.

The more important finding: both evaluators independently flagged the Customization section for lacking concrete before-and-after examples, naming "changing the scoring scale" and "adding a sixth criterion" as unaddressed cases. Both are wrong — this README has complete worked examples for both. This is a confirmed, verifiable instance of the [Occasional factually incorrect claims](#known-limitations) limitation, caught across two independent scripts agreeing on the same false finding. Two evaluators agreeing is not evidence a claim is correct — verify any specific completeness or clarity claim against the actual source text before acting on it.

* Both evaluators agreed on four of five criteria this run; they diverged only on Structure, where RAG-enhanced's lower score came with a standards-traceable explanation baseline didn't have.
* Agreement between the two modes doesn't make a finding true — see the shared factual error above.
* RAG-enhanced's retrieval trace (the `Retrieved N guideline chunk(s)` list preceding its JSON output) is what makes its reasoning checkable — verify a claim by looking at which guideline chunk it cites, not just by trusting the score.

> **Note**: You may see occasional product-related feedback rather than documentation-related feedback. For example, "The instruction to 'email api-support@bookhub.com' is a procedural workaround that should be replaced with an automated token endpoint." If an instruction describes how the product actually works, you can disregard the feedback.

## Assumptions

This guide assumes basic familiarity with Git, Python, and the command line.

## Prerequisites

* Python 3.x.
* Git &mdash; needed to clone the `doc-quality-evaluator` repository.
* A code editor, such as VS Code, or a plain-text editor for editing files. You run the evaluator from the terminal.
* An Anthropic API account and API key. Limit access to your Anthropic key to those who need it. Do not store it in a version control system. When you add it to the `.env` file, it's never pushed to your GitHub repository.

> **API costs**: An Anthropic API key is required. Anthropic accounts receive a small amount of starter credits for API calls. After that, usage is billed per token. The cost to run the evaluator against a typical doc is a fraction of a cent per evaluation. See [Anthropic's pricing page](https://claude.com/pricing) for current rates.

## Supported formats

This section describes supported file formats for reference.

* Markdown (`.md`): fully supported and tested
* MDX (`.mdx`): fully supported and tested

> **Note**: The evaluator reads plain text files. Other plain text formats, such as `.txt`, may work but have not been tested. Binary formats such as `.docx` are not supported.

### MDX handling

The evaluator preprocesses `.mdx` files before evaluation. The following MDX-specific syntax is stripped:

* YAML frontmatter (the `---` block at the top of the file)
* `import` statements
* JSX component tags, such as `<Note>`, `<Warning>`, and `<CodeGroup>`
* MDX expression comments, such as `{/* comment */}`

Content inside JSX components is preserved &mdash; only the tags are removed. For example, the text inside a `<Note>` block is still evaluated.

> **Important**: Always edit the source `.mdx` file in your docs repository first, then copy the updated file to the `samples/` folder. Files in `samples/` are evaluation inputs, never sources of truth. The evaluation reflects content quality, not MDX component rendering.

### Classifying documents with `docType`

The `RAG-enhanced` evaluator reads a `docType` field from a document's frontmatter and uses it to ground the Structure and Completeness criteria in the matching Diátaxis checklist &mdash; instead of asking the model to infer the type from content alone.

Use one of six values: `tutorial`, `how-to`, `reference`, `explanation`, `overview`, or `integration-guide`. `overview` is a practical addition beyond strict Diátaxis, for navigational index or hub pages. `integration-guide` is a how-to specialization for implementation walkthroughs with code and a testing step — it's scored structurally as `how-to`, but additionally grounds Completeness against Integration Guide Standards (including error-handling guidance), which plain how-to guides aren't held to.

```yaml
---
docType: overview
---
```

When a `docType` is declared, `build_index.py` guarantees that type's own guideline chunk from `diataxis_types.md` is retrieved, regardless of how semantic similarity ranks it against the document being evaluated. See [Retrieval diagnostics](#retrieval-diagnostics) for what this looks like in the console output.

If `docType` is omitted, the evaluator falls back to inferring the type from the document's content pattern. This is less reliable &mdash; for example, an overview page that lists endpoints and status codes can read enough like a Reference doc that the evaluator scores it against Reference completeness requirements instead of Overview requirements.

This applies to both `.md` and `.mdx` files, not just MDX.

> **Important**: Frontmatter delimiters must be exactly `---` (three hyphens) on their own line, both opening and closing, with nothing before the first one. A missing or malformed delimiter causes `docType` &mdash; and every other frontmatter field &mdash; to silently go unread; no error is raised. Confirm it worked by checking that the `Evaluating: <path>` console line shows `(docType: <value>)`. If it doesn't, the frontmatter isn't being parsed.

## Repository structure

The repository contains the following files.

```text
├── chroma_db/                                        # The local ChromaDB vector store
├── images/
│   ├── baseline-evaluation-pipeline.png              # baseline evaluation workflow diagram
│   ├── RAG_enhanced_output_sample.png                # RAG-enhanced evaluation output sample
│   └── RAG-enhanced-evaluation-pipelines.png         # RAG-enhanced evaluation workflow diagram
├── json_samples/
│   ├── RAG_enhanced_quickstart_mdx_sample.json       # RAG-enhanced sample for quickstart.mdx
│   ├── RAG_enhanced_webhooks_admin_ui_md_sample.json # RAG-enhanced sample for webhooks-Admin-UI.md
├── knowledge_base/                                   # Guideline files used by evaluate_rag.py
│   ├── api_doc_standards.md                          # Standards for complete, accurate, and usable REST API documentation
│   └── diataxis_types.md                             # Definitions and standards for the four Diátaxis documentation types, plus the practical overview addition
├── samples/
│   ├── quickstart.mdx                                # Sample MDX doc used for testing
│   └── webhooks-Admin-UI.md                          # Sample Markdown doc used for testing
├── txt_samples/
│   ├── baseline_readme_md_sample.txt                 # Baseline sample for README.md
│   ├── RAG_enhanced_readme_md_sample.txt             # RAG-enhanced sample for README.md
│   └── sample_comparison_report.txt                  # Side-by-side comparison of baseline and RAG-enhanced results for README.md
├── build_index.py                                    # Indexes the knowledge_base/ folder into the local ChromaDB vector store used by evaluate_rag.py
├── evaluate.py                                       # Main evaluation script
├── evaluate_rag.py                                   # Extends evaluate.py by retrieving relevant documentation guidelines from the local ChromaDB vector store before calling the Anthropic API
├── LICENSE                                           # MIT License
├── README.md                                         # The doc-quality-evaluator overview
└── requirements.txt                                  # Python dependencies
```

## Setup

Before running the evaluator, complete the following steps.

1. Clone the `doc-quality-evaluator` repository to your machine.
2. Run `pip install -r requirements.txt` in your local Python environment to install the evaluator's Python dependencies.
3. Add a `.env` file to the root level of the cloned repository and include your Anthropic key.

    ```text
    ANTHROPIC_API_KEY=your-actual-key-here
    ```

4. (`RAG-enhanced` evaluation only) Run `python3 build_index.py` to index the `knowledge_base/` folder into the local ChromaDB vector store. Run this once before your first `evaluate_rag.py` run, and re-run it any time you add or update knowledge base files.

    ```text
    python3 build_index.py
    ```

5. Add your Markdown or MDX file to the `samples/` folder.

    > **Note**: For MDX files, always edit the source `.mdx` file in your docs repository first, then copy the updated file to `samples/`.

6. From a terminal, run the `evaluate.py` or `evaluate_rag.py` command and include the path to the file in the `samples/` folder.

    ```text
    python3 evaluate.py samples/my-doc.mdx
    python3 evaluate_rag.py samples/my-doc.mdx
    ```

7. Verify the raw JSON results appear in the output. For example, the `RAG-enhanced` output will look like:

    ![`RAG-enhanced` output example](./images/RAG_enhanced_output_sample.png)

8. Repeat steps 5-7 for each additional Markdown or MDX file.

## Output reference

This section describes the JSON output format for reference.

### Output fields

| Field | Description |
| ----- | ----------- |
| `clarity` | Score and feedback on writing clarity and ambiguity |
| `completeness` | Score and feedback on missing parameters, responses, or error codes |
| `accuracy` | Score and feedback on code example correctness |
| `consistency` | Score and feedback on terminology, tone, and formatting |
| `structure` | Score and feedback on Diátaxis content type alignment |
| `overall` | Composite score and summary of primary improvement areas |

## Customization

This section is optional. Complete it only if you want to adapt the evaluator to your own documentation standards.

### Customize the system prompt

The evaluation criteria, scoring scale, and doc context are all controlled by the `SYSTEM_PROMPT` variable in `evaluate.py` and `evaluate_rag.py`. Modify that string to adapt the evaluator to your own doc standards, style guide, or content types.

> **Note**: The `SYSTEM_PROMPT` is the single point of customization for the `baseline` evaluator. Change that string, and the entire evaluation changes.

Every customization follows the same pattern: find the relevant lines in `SYSTEM_PROMPT` and replace them. The following before-and-after examples show the pattern.

#### Targeting a different doc domain

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

#### Replacing the Diátaxis criterion with a style guide check

Replace this:

```text
5. STRUCTURE — Does the content follow the appropriate Diátaxis type 
   (tutorial / how-to / reference / explanation / overview)?
```

> **Note**: `evaluate.py` (baseline) already lists the same five types in its own `SYSTEM_PROMPT`. However, baseline has no way to honor a document's declared `docType` — `strip_mdx()` removes the entire frontmatter block before the content reaches the model, and there's no retrieval step to guarantee a type's checklist gets included. Baseline always infers the Diátaxis type from content alone; only `RAG-enhanced` reads and grounds against an explicit `docType`.

With this:

```text
5. STYLE GUIDE — Does the content follow the Microsoft Writing Style 
   Guide conventions for tone, voice, and terminology?
```

#### Changing the scoring scale

You can change the 1–5 scale to 1–10 or a pass/fail system by updating the prompt instructions.

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

#### Adding a sixth criterion

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

> **Important**: Make this change in both `evaluate.py` and `evaluate_rag.py` if you want the new criterion scored in both modes, and add the new field to the Output fields table in [Output reference](#output-reference).

#### Replacing completeness with a release-notes-specific criterion

Swap a criterion's focus entirely rather than adding one — useful when a doc type (like release notes) has a different definition of "complete."

Replace this:

```text
2. COMPLETENESS — Are all parameters, responses, and error codes documented?
```

With this:

```text
2. BREAKING CHANGES — Are all breaking changes clearly flagged, with 
   migration guidance provided for each one?
```

> **Note**: If you rename a criterion's label, also update the corresponding JSON key in `SYSTEM_PROMPT`'s output format instructions (e.g., `"completeness"` to `"breaking_changes"`) and the Output fields table in [Output reference](#output-reference), so the prompt, the JSON schema, and the docs all stay in sync.

### Customize the knowledge base

The `RAG-enhanced` evaluator has a second customization point: the `knowledge_base/` folder. The evaluator retrieves guideline chunks from this folder and grounds its assessment in them, so adding your own standards changes what the evaluation is measured against. For example:

* Add your company style guide as a Markdown file.
* Add product-specific documentation standards.
* Replace `api_doc_standards.md` with standards for your own doc domain.

Structure each file with `##` headers &mdash; `build_index.py` splits files on level-2 headers, and each section becomes a separate retrievable chunk.

`build_index.py` also tags the type-defining sections across the knowledge base with metadata, matched by exact header text. The four Diátaxis type sections plus `## Overview / Index Pages` live in `diataxis_types.md`; `## Integration Guide Standards` lives in `api_doc_standards.md`.

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

> **Important**: If you rename or restructure these headers in `diataxis_types.md` or `api_doc_standards.md`, update `DOCTYPE_HEADERS` in `build_index.py` to match. A mismatch fails silently &mdash; retrieval falls back to similarity-only ranking for that type instead of raising an error.

> **Important**: Re-run `python3 build_index.py` after adding or updating knowledge base files. The vector index does not update automatically.

### Tips for writing effective prompts

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

## Interpreting evaluator feedback

Scores are a starting point, not a verdict. Read evaluator output carefully and avoid common interpretation mistakes.

### Score ranges

| Score | Interpretation |
| ----- | -------------- |
| 5 | No significant gaps identified |
| 4 | Minor gaps — review feedback and decide whether to act |
| 3 | Meaningful gaps — investigate and revise where appropriate |
| 2 | Significant gaps — document likely needs revision |
| 1 | Major gaps — document may need to be restructured |

### Watch for false positives

The evaluator does not know your document type, platform, or style guide. Watch for common false positives:

* **Explanation docs flagged for missing steps or code examples**: Explanation docs should not include procedural steps or code examples; instead, link to how-to guides.
* **Requesting error response tables in how-to guides**: If the guide already links to a reference doc containing error codes, the completeness gap is addressed.
* **Snake_case Python variable names and camelCase JSON field names flagged as inconsistent**: These are correct conventions for their respective languages and contexts, not inconsistencies.
* **Explicitly disclosed known inconsistencies flagged as documentation defects**: When docs transparently acknowledge a real product-level inconsistency (e.g., a schema noting specific fields use snake_case while the rest of the API uses camelCase, with a note that it will be fixed), the evaluator still penalizes the consistency score. Disclosing a known issue is correct documentation practice — the inconsistency lives in the product, not the docs. Confirmed recurring across three evaluation runs on the same finding.
* **Flagging intentional style choices as grammar errors**: Technical writing conventions such as imperative voice and short sentences may trip up general grammar evaluation.
* **Product-design feedback presented as documentation gaps**: The evaluator may recommend changing how the product works (for example, replacing an email-based token process with an automated endpoint). If the documentation accurately describes actual product behavior, the docs are correct &mdash; disregard the feedback.
* **Overview, index, and explanation (conceptual guide) pages flagged as incomplete reference documents**: Declaring the correct `docType` (see [Classifying documents with `docType`](#classifying-documents-with-doctype)) now grounds the Structure and Completeness criteria in that type's own checklist via guaranteed retrieval, which substantially reduces this false positive. Residual risk remains when `docType` is omitted (the evaluator falls back to inferring type from content) or when a document links out to a reference page that doesn't actually cover the deferred detail &mdash; the evaluator has no visibility into linked pages' content, so check that the linked page actually covers what's missing before treating a low completeness/structure score as real.

### Cross-reference against the Diátaxis document type

Each Diátaxis document type has different completeness standards. Apply the right criteria for the doc type before acting on feedback:

* **Tutorials** should include prerequisites, step-by-step instructions, and a concrete outcome. Missing reference material is not a gap.
* **How-to guides** should include steps, a response section, and links to related content. Missing conceptual background is not a gap &mdash; link to the explanation doc instead.
* **Integration guides** (`docType: integration-guide`) follow the same requirements as how-to guides, plus error-handling guidance for common failures. Missing this is a legitimate completeness gap for integration guides — it isn't for plain how-to guides.
* **Explanation docs** should answer "why" and "what." Missing code examples or procedural steps is not a gap.
* **Reference docs** should be complete and accurate. Missing examples or error codes are legitimate gaps.
* **Overview and index pages** should provide a brief statement of what the section covers plus categorized links to the actual content. Missing parameter tables, schemas, error codes, numbered steps, or conceptual depth is not a gap &mdash; that content belongs on the linked pages.

### Iterate, don't over-optimize

Chasing a 5 on every criterion can lead to over-documentation. A how-to guide that scores 4 on structure because it contains a response section that follows standard how-to guide conventions is not a failure. Use judgment when deciding whether to act on feedback.

### Persistent low scores signal real gaps

If the same criterion scores 3 or below across multiple evaluation runs after revisions, that's a genuine signal worth addressing. Persistent low scores on accuracy or consistency are a higher priority than persistent low scores on completeness for overview and conceptual docs.

### Example: justified score of 4

A conceptual guide scores 4 on completeness because it lacks documentation for request parameters. This is a false positive — parameter documentation belongs in the reference doc, not the explanation doc. Verify the reference doc contains the parameters and link to it; do not add a parameters table to the conceptual guide.

### Expect run-to-run variance

LLM evaluations are not deterministic. The same document can receive slightly different scores and feedback across runs with no changes to the content. A one-point difference between runs is noise, not signal. Watch for feedback that persists across multiple runs — and note that persistent feedback can also reflect the evaluator's strictness rather than a genuine gap, as when feedback softens in wording while the score holds steady.

## Roadmap

This document is primarily written to help developers get up and running with the `doc-quality-evaluator` and to explain the technical details you need clearly. Refer to this roadmap for future evaluator features.

1. **RAG evaluation**: Completed July 2026. Read and evaluate Markdown and MDX files using RAG and output a report.
2. **MDX support**: Completed July 2026. Extend format support to `.mdx` files.
3. **Batch evaluation**: Read and evaluate a set of files (Markdown, OpenAPI YAML, etc.) and output a report.
4. **Markdown report generation**: Generate a Markdown report.
5. **Word document support**: Extend format support to `.docx` files using python-docx.
6. **Scoring thresholds and pass/fail behavior**: Define minimum score thresholds per criterion. Flag or fail evaluation when scores fall below the threshold — supports enforcement in CI/CD pipelines.
7. **GitHub Action integration**: Wire the evaluator script into a GitHub Action so every PR gets an automated doc quality check alongside your existing linting.
8. **Line-level feedback**: Include line numbers in evaluation feedback to help writers locate specific issues without manual searching.

## Known limitations

* **No visibility into linked or complementary pages**: The evaluator scores one file in isolation and cannot verify what a linked page actually contains. For documents with a declared `docType`, guaranteed retrieval of that type's own checklist (see [Classifying documents with `docType`](#classifying-documents-with-doctype)) now correctly treats deferral to a linked page as expected behavior for overview and explanation types, rather than a completeness gap. This limitation still applies when `docType` is omitted, or when a linked page is claimed to cover something it doesn't actually cover. Before trusting a low completeness/structure score, check whether the missing content lives one link away.

* **Disclosed caveats scored as if undisclosed**: When a document explicitly flags its own limitation — a known naming inconsistency, illustrative-only code examples — the evaluator still penalizes it as a defect. It doesn't appear to register in-document disclaimers as mitigating context.

* **Occasional factually incorrect claims**: In at least five runs, feedback asserted content was missing or absent that was plainly present in the text: a documented `410 Gone` response, a link to rate-limit details, a claim that this README's Customization section lacked before-and-after examples for cases that already had them, a claim that an integration guide's code sample didn't import `uuid` or `requests` when both were its first two lines, and a claim that a how-to guide's Python example omitted `import requests` when it was line one of the block. These aren't scope disagreements — verify the specific claim against the source text before acting on it, regardless of which evaluation mode produced it.

* **Inconsistent criterion assignment**: The same condition (missing code examples) was scored as accuracy-neutral in one run and accuracy-penalizing in another. Findings should be checked against the actual guideline criterion, not assumed consistent run-to-run.

* **Nondeterministic JSON parse failures**: The evaluator asks the model to return raw JSON, but the model occasionally emits unescaped double quotes inside a feedback string (e.g., quoting `"Update all API URLs"` mid-sentence), which produces invalid JSON. The repair fallback in both scripts recovers many cases but not all; when it can't, the run prints a `JSON parse error` and the raw response instead of parsed results. This is nondeterministic — the same document can parse cleanly on one run and fail on the next with no content change (confirmed on the v2 migration guide, which failed once on unescaped quotes and parsed on an immediate rerun). If you hit it, rerun before assuming anything is wrong with the document; the scores in the raw dump are still valid if you need them before rerunning.

## Troubleshooting

Refer to this section if you encounter any issues while running the evaluator.

### Context-blind feedback

The evaluator has no awareness of how a document fits into a larger documentation set. It evaluates each file in isolation. Feedback about missing definitions, unexplained terminology, or incomplete scope may reflect content that exists elsewhere in your documentation — for example, in a top-level README or a linked reference document.

Always apply editorial judgment by considering the context of the entire documentation set, not just individual files, before acting on evaluator feedback.

### FileNotFoundError: [Errno 2] No such file or directory: 'my_doc.md'

The folder and filename are incorrect or missing. Verify that the folder and filename are correct, then try again.

### Error: Collection 'doc_guidelines' not found

The `RAG-enhanced` evaluator can't find the ChromaDB vector index. Run `python3 build_index.py` to create the index, then run `evaluate_rag.py` again.

### Error code 400: user messages must have non-empty content

The file the evaluator is pointing to is empty or has no readable content. Open the file in your editor and confirm it contains text. If the file is empty, add content and rerun the evaluator. Here's an example of the error message:

```text
anthropic.BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'messages.0: user messages must have non-empty content'}, 'request_id': 'req_011CaAADrvnXeUYsBcu8jQW7'}
```

### JSON parse error

If the model's response can't be parsed as JSON, the evaluator prints the parse error and the raw response for debugging, then exits. This can happen when the response contains unescaped quotes or is truncated. Run the evaluation again — if the error persists for a long document, the response may be exceeding the token limit (see `max_tokens` in the script).

### Feedback references broken or unverifiable links

The evaluator cannot click or verify links, so it's penalizing you for not embedding content inline. If the evaluator flags links as broken or unverifiable, manually test the links before making any changes. Use a link checker such as GitHub Actions for automated verification.

### Unicode characters appear in the JSON output

If Unicode characters appear in the JSON output, verify that `ensure_ascii=False` appears in the `evaluate.py` or `evaluate_rag.py` script and try again.

### 0 evaluation score

A zero (`0`) in the evaluation score indicates something went wrong with the evaluation. Here are the scenarios that would trigger a 0:

* **Malformed or empty input file**: If the evaluator reads an empty `.md` file, the model has nothing to evaluate and might return the unfilled template.
* **Prompt misfire**: If the system prompt is truncated or corrupted, the model might return the default structure.
* **Non-doc input**: If someone accidentally points the evaluator at a non-doc file, such as a config file or script, the model might not know how to score it.

## Changelog

### July 2026

* Added the `RAG-enhanced` evaluation feature (`evaluate_rag.py`, `build_index.py`, and the `knowledge_base/` folder).
* Added `docType` frontmatter support to `evaluate_rag.py`. The declared type is read and passed into the evaluation prompt, so the Structure and Completeness criteria are graded against that type's own checklist instead of an inferred one.
* Added `overview` as a fifth, practical (non-canonical) Diátaxis type in `diataxis_types.md`, for navigational index and hub pages.
* Added `integration-guide` as a sixth `docType` &mdash; a how-to specialization for implementation walkthroughs, scored structurally as `how-to` but additionally grounding Completeness against the Integration Guide Standards in `api_doc_standards.md`. Tagged that section in `DOCTYPE_HEADERS` for guaranteed retrieval.
* Added guaranteed retrieval to `build_index.py` and `evaluate_rag.py`: the declared `docType`'s own guideline chunk is always included in retrieval via metadata filtering, regardless of similarity ranking.
* Re-ran both evaluators against the current README and updated `sample_comparison_report.txt` with the new results, including a confirmed factual-error finding now folded into Known limitations. Clarified that the report's `knowledge_base` and `retrieved_chunks` fields are compiled from console retrieval diagnostics, not part of the evaluator's own JSON schema. Converted the README-related sample outputs to `.txt` in `txt_samples/` to capture full console output.
* Added support for the MDX format. MDX-specific syntax (frontmatter, imports, JSX tags) is stripped before evaluation; content inside JSX components is preserved.
* Changed how you specify the file to evaluate. Previous setup instructions said to add your file to the `samples/` folder, update `DOC_PATH` in `evaluate.py`, and run the `python3 evaluate.py` command in the terminal. Both scripts now require the file path as a command-line argument, for example:

    ```text
    python3 evaluate.py samples/my-doc.mdx
    python3 evaluate_rag.py samples/my-doc.mdx
    ```

* Increased `max_tokens` from 1024 to 2048 in `evaluate_rag.py` to prevent truncated responses on longer documents.
* Added JSON parse error handling. If the model's response can't be parsed, the evaluator now prints the parse error and the raw response for debugging instead of an unhandled traceback.
* Ported JSON parse error handling from `evaluate_rag.py` to `evaluate.py`, so both scripts print the parse error and raw response instead of an unhandled traceback.
* Added run-to-run variance guidance based on a second evaluation of this README; updated the comparison report's version note accordingly.

### May 2026

* **Fix (consistency criterion)**: The evaluator incorrectly flagged camelCase JSON field names (e.g., `bookId`) and snake_case Python variable names (e.g., `book_id`) as inconsistent. These reflect correct language conventions. The consistency prompt now distinguishes cross-language naming differences (not a flag) from genuine inconsistencies such as mixed conventions within a single language or mismatched field names passed between languages.

---

Last updated: July 2026
