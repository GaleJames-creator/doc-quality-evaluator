# Interpreting evaluator feedback

Scores are a starting point, not a verdict. Read evaluator output carefully and avoid common interpretation mistakes.

## Score ranges

| Score | Interpretation |
| ----- | -------------- |
| 5 | No significant gaps identified |
| 4 | Minor gaps&mdash;review feedback and decide whether to act |
| 3 | Meaningful gaps&mdash;investigate and revise where appropriate |
| 2 | Significant gaps&mdash;document likely needs revision |
| 1 | Major gaps&mdash;document may need to be restructured |

## What the evaluator reliably catches

Most of this page is about feedback to discount, which understates what the tool is for. Its strongest results are internal contradictions between parts of a document that each read correctly on their own &mdash; the errors a human reviewer skims past because nothing in any single sentence looks wrong.

Two findings from a threshold-4 run over a published API documentation set, both confirmed and fixed:

* **A specification that contradicted its own examples.** A data models page declared a `language` field as "ISO 639-1," while every example in the repository used `en-US` &mdash; a BCP 47 language tag, not an ISO 639-1 code. One wrong phrase invalidated roughly eighteen examples across the set. Correcting the specification validated all of them at once.
* **A request that couldn't produce its own response.** A pagination guide sent `limit: 100`, and the response beneath it showed `totalItems: 87` across `totalPages: 5`. Eighty-seven items at a hundred per page is one page, not five. The prose was clear, the JSON was valid, and the two halves were irreconcilable.

Neither is a style question, and neither would surface in a spell check, a link check, or a lint pass. Both stem from reading a specification against the examples that implement it, which is exactly the comparison that gets skipped when a document is long and each part was written at a different time.

The practical implication: weigh feedback that cites two specific things and says they disagree far more heavily than feedback about missing sections or structural fit. The first kind is checkable and has been right; the second is where the category errors and false positives cluster.

## Watch for false positives

The evaluator does not know your document type, platform, or style guide. Watch for common false positives:

* **Explanation docs flagged for missing steps or code examples**: Explanation docs should not include procedural steps or code examples; instead, link to how-to guides.
* **Requesting error response tables in how-to guides**: If the guide already links to a reference doc containing error codes, the completeness gap is addressed.
* **Snake_case Python variable names and camelCase JSON field names flagged as inconsistent**: These are correct conventions for their respective languages and contexts, not inconsistencies.
* **Explicitly disclosed known inconsistencies flagged as documentation defects**: When docs transparently acknowledge a real product-level inconsistency (e.g., a schema noting specific fields use snake_case while the rest of the API uses camelCase, with a note that it will be fixed), the evaluator still penalizes the consistency score. Disclosing a known issue is correct documentation practice&mdash;the inconsistency lives in the product, not the docs. Confirmed recurring across three evaluation runs on the same finding.
* **Flagging intentional style choices as grammar errors**: Technical writing conventions such as imperative voice and short sentences may trip up general grammar evaluation.
* **Product-design feedback presented as documentation gaps**: The evaluator may recommend changing how the product works (for example, replacing an email-based token process with an automated endpoint). If the documentation accurately describes the product behavior, the docs are correct &mdash; disregard the feedback.
* **Overview, index, and explanation (conceptual guide) pages flagged as incomplete reference documents**: Declaring the correct `docType` (see [Classifying documents with `docType`](supported-formats.md#classifying-documents-with-doctype)) now grounds the Structure and Completeness criteria in that type's own checklist via guaranteed retrieval, which substantially reduces this false positive. Residual risk remains when `docType` is omitted (the evaluator falls back to inferring type from content) or when a document links out to a reference page that doesn't actually cover the deferred detail &mdash; the evaluator has no visibility into linked pages' content, so check that the linked page actually covers what's missing before treating a low completeness/structure score as real.

## Cross-reference against the Diátaxis document type

Each Diátaxis document type has different completeness standards. Apply the right criteria for the doc type before acting on feedback:

* **Tutorials** should include prerequisites, step-by-step instructions, and a concrete outcome. Missing reference material is not a gap.
* **How-to guides** should include steps, a response section, and links to related content. Missing conceptual background is not a gap &mdash; link to the explanation doc instead.
* **Integration guides** (`docType: integration-guide`) follow the same requirements as how-to guides and include error-handling guidance for common failures. Missing this is a legitimate completeness gap for integration guides&mdash;it isn't for plain how-to guides.
* **Explanation docs** should answer "why" and "what." Missing code examples or procedural steps are not gaps.
* **Reference docs** should be complete and accurate. Missing examples or error codes are legitimate gaps.
* **Overview and index pages** should provide a brief statement of what the section covers plus categorized links to the actual content. Missing parameter tables, schemas, error codes, numbered steps, or conceptual depth is not a gap &mdash; that content belongs on the linked pages.

## A flat score of 1 means out of scope, not poor quality

When every criterion scores exactly 1 and each feedback sentence says the criteria don't apply, the evaluator is refusing the document rather than judging it. The tool schema requires an integer from 1 to 5 for every criterion, so refusal has nowhere to go but the floor.

Distinguish this from a genuinely weak document, which scores unevenly. Clarity and consistency survive even when completeness collapses, because prose can be well written while omitting required reference material. A template scaffold in one run scored 2 on clarity, 1 on completeness, 3 on accuracy, 2 on consistency, and 1 on structure &mdash; an uneven profile, and a real reading. A flat 1/1/1/1/1 is not.

## Case study: evaluating this documentation set

The nine pages in `docs/` were scored against the shipped knowledge base. Seven landed between 4.6 and 5.0, three of them at a perfect 5. Two failed:

| Page                 | Overall | Profile           |
| -------------------- | ------- | ----------------- |
| `customization.md`   | 1.0     | 1 / 1 / 1 / 1 / 1 |
| `output-reference.md`| 2.8     | 3 / 2 / 4 / 4 / 2 |

Same author, same day, same rubric. `customization.md` is not four points worse-written than the pages that scored 5. It is the page furthest from anything resembling an API, and it fell hardest outside a rubric built for API and developer documentation. Its feedback said so plainly on every criterion: "completeness criteria for parameters, responses, and error codes do not apply," "does not fit any of the Diátaxis types," and finally "This document is out of scope for evaluation."

Acting on that feedback would mean adding endpoints, parameters, and error codes to a guide about editing a system prompt &mdash; inventing an API to satisfy a score. The scores stand uncorrected for that reason.

`output-reference.md` scored unevenly, which is the profile worth reading closely. Buried in its feedback was one fair observation: the page's purpose and audience were ambiguous. Its opening line still read "This section outlines..." &mdash; a leftover from when it was a section of the README rather than a page of its own. That sentence was rewritten, along with the same artifact on three sibling pages. The rest of the feedback, asking for HTTP methods and status codes in a document that describes the evaluator's own JSON output, was the same category error.

The underlying cause is that `knowledge_base/` is specific to fintech and API documentation, and these pages are neither of those. Properly scoring tooling documentation would mean pointing the evaluator at a knowledge base written for it &mdash; which is what [Customization](./customization.md) explains how to do. The page that scored 1 documents the fix for why it scored 1.

## Iterate, don't over-optimize

Chasing a 5 on every criterion can lead to over-documentation. A how-to guide that scores 4 on structure because it contains a response section that follows standard how-to guide conventions is not a failure. Use judgment when deciding whether to act on feedback.

## Persistent low scores signal real gaps

If the same criterion scores 3 or below across multiple evaluation runs after revisions, that's a genuine signal worth addressing. Persistent low scores on accuracy or consistency are a higher priority than persistent low scores on completeness for overview and conceptual docs.

## Example: justified score of 4

A conceptual guide scores 4 on completeness because it lacks documentation for request parameters. This is a false positive&mdash;parameter documentation belongs in the reference doc, not the explanation doc. Verify the reference doc contains the parameters and include a link to it; do not add a parameters table to the conceptual guide.

## Expect run-to-run variance

LLM evaluations are not deterministic. The same document can receive slightly different scores and feedback across runs with no changes to the content. A one-point difference between runs is noise, not signal. Watch for feedback that persists across multiple runs&mdash;and note that persistent feedback can also reflect the evaluator's strictness rather than a genuine gap, as when feedback softens in wording while the score holds steady.

## Known limitations

* **No visibility into linked or complementary pages**: The evaluator scores one file in isolation and cannot verify what a linked page actually contains. For documents with a declared `docType`, guaranteed retrieval of that type's own checklist (see [Classifying documents with `docType`](supported-formats.md#classifying-documents-with-doctype)) now correctly treats deferral to a linked page as expected behavior for overview and explanation types, rather than a completeness gap. This limitation still applies when `docType` is omitted, or when a linked page is claimed to cover something it doesn't actually cover. Before trusting a low completeness/structure score, check whether the missing content lives one link away.

* **Snippet content is never evaluated in context**: MDX `import` statements and JSX tags are stripped before evaluation (see [MDX handling](supported-formats.md#mdx-handling)), so a reusable snippet's text is not evaluated as part of the pages that include it. Evaluated on its own, a snippet is an out-of-context fragment and scores poorly for missing structure it was never meant to carry &mdash; prerequisites lists, endpoint metadata, surrounding schema. Neither reading is useful, so snippet files are best excluded with `skip-evaluation: true`; just be aware that their content will then go unreviewed by the evaluator and will need human review instead.

* **Disclosed caveats scored as if undisclosed**: When a document explicitly flags its own limitation&mdash;a known naming inconsistency, illustrative-only code examples&mdash;the evaluator still penalizes it as a defect. It doesn't appear to register in-document disclaimers as mitigating context.

* **Occasional factually incorrect claims**: In at least five runs, feedback asserted content was missing or absent that was plainly present in the text: a documented `410 Gone` response, a link to rate-limit details, a claim that the customization guide lacked before-and-after examples for cases that already had them, a claim that an integration guide's code sample didn't import `uuid` or `requests` when both were its first two lines, a claim that a how-to guide's Python example omitted `import requests` when it was line one of the block, a repeat of that same missing-imports claim against a code-examples page whose block opens with `import requests`, `import time`, and `import uuid`, and an off-by-one error alleged in a pagination loop that fetches every page correctly. These aren't scope disagreements&mdash;verify the specific claim against the source text before acting on it, regardless of which evaluation mode produced it. Claims about missing imports have been wrong every time so far.

* **Inconsistent criterion assignment**: The same condition (missing code examples) was scored as accuracy-neutral in one run and accuracy-penalizing in another. Check findings against the actual guideline criterion, not assumed consistent run-to-run.

* **Nondeterministic JSON parse failures (baseline `evaluate.py` only)**: `evaluate.py` asks the model to return raw JSON, and the model occasionally emits unescaped double quotes inside a feedback string (e.g., `("winner")`), which produces invalid JSON that the repair fallback can't always recover&mdash;the run then prints a `JSON parse error` and the raw response instead of parsed results. The RAG evaluator (`evaluate_rag.py`, `evaluate_core.py`, and the CI runner) is no longer affected: it uses structured tool output, so the model returns an already-parsed object with no JSON-in-text step to fail. If you hit a parse error on the baseline evaluator, rerun it or use the RAG evaluator instead.

---

[Back to the doc-quality-evaluator README](../README.md)
