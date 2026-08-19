# Output reference

This page documents the JSON the evaluator returns: what each field means, how the response is structured, and how `baseline` and `RAG-enhanced` results differ for the same document. Read it when you're interpreting output or parsing it programmatically. It describes the evaluator's own output format, not an API that the evaluated documents belong to.

## Output fields

| Field | Description |
| ----- | ----------- |
| `clarity` | Score and feedback on writing clarity and ambiguity |
| `completeness` | Score and feedback on missing parameters, responses, or error codes |
| `accuracy` | Score and feedback on code example correctness |
| `consistency` | Score and feedback on terminology, tone, and formatting |
| `structure` | Score and feedback on Diátaxis content type alignment |
| `overall` | Composite score and summary of primary improvement areas |

## JSON output format

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

## JSON evaluation results

The `baseline` and `RAG-enhanced` evaluators return status messages and evaluation results.

The evaluation results are in raw JSON. They do not include any explanations, preambles, or Markdown code fences. For example, when the evaluator reviewed this repository's README&mdash;then a single document, before it was split into this documentation set&mdash;it provided the following feedback:

```text
All major setup steps and output fields are documented, but the customization section lacks concrete examples of what the modified SYSTEM_PROMPT should look like for the suggested use cases.
```

You can see the response to this Diátaxis criterion feedback. If you prefer a style guide check, see [Replacing the Diátaxis criterion with a style guide check](customization.md#replacing-the-diátaxis-criterion-with-a-style-guide-check).

See [Comparing `baseline` and `RAG-enhanced` JSON results](#comparing-baseline-and-rag-enhanced-json-results) for additional details.

See [RAG_enhanced_webhooks_admin_ui_md_sample.json](../json_samples/RAG_enhanced_webhooks_admin_ui_md_sample.json) and [RAG_enhanced_quickstart_mdx_sample.json](../json_samples/RAG_enhanced_quickstart_mdx_sample.json) for examples of the JSON results.

After you update the Markdown doc based on the evaluator's feedback, run the evaluation again. You should see the scores and evaluations improve.

## Comparing `baseline` and `RAG-enhanced` JSON results

Both evaluators were run against the same document&mdash;this repository's README, before the split&mdash;and the results are more useful as a lesson in reading evaluator output critically than as a "RAG always wins" demonstration. The [baseline_readme_md_sample.txt](../txt_samples/baseline_readme_md_sample.txt) file shows the `baseline` result, [RAG_enhanced_readme_md_sample.txt](../txt_samples/RAG_enhanced_readme_md_sample.txt) shows the `RAG-enhanced` result including its retrieval trace, and [sample_comparison_report.txt](../txt_samples/sample_comparison_report.txt) shows the combined side-by-side comparison with additional analysis, without you having to run either script.

The headline of this run: neither evaluator returned a perfect score, and the two mostly agreed. Baseline scored clarity 4, completeness 4, accuracy 5, consistency 5, structure 5. RAG-enhanced matched on the first four and scored structure one point lower&mdash;for a reason worth noting: its Structure feedback is grounded in the classification framework itself ("this document functions primarily as a how-to guide... the Roadmap section doesn't fit the how-to-guide task orientation"), while baseline's perfect Structure score offers no standard to check it against. That traceability, not the raw score, is what RAG grounding actually adds here. That Structure finding was later acted on: the README did mix document types, and splitting it into this documentation set is what resolved it&mdash;a case where the lower score was the more useful one.

The more important finding: both evaluators independently flagged the Customization section for lacking concrete before-and-after examples, naming "changing the scoring scale" and "adding a sixth criterion" as unaddressed cases. Both are wrong&mdash;the [Customization](customization.md) guide, then a section of the README, has complete worked examples for both. This is a confirmed, verifiable instance of the [Occasional factually incorrect claims](interpreting-feedback.md#known-limitations) limitation, caught across two independent scripts that agree on the same false finding. Two evaluators agreeing is not evidence a claim is correct&mdash;verify any specific completeness or clarity claim against the actual source text before acting on it.

* Both evaluators agreed on four of five criteria in this run; they diverged only on Structure, where RAG-enhanced's lower score came with a standards-traceable explanation baseline didn't have.
* Agreement between the two modes doesn't make a finding true&mdash;see the shared factual error above.
* RAG-enhanced's retrieval trace (the `Retrieved N guideline chunk(s)` list preceding its JSON output) is what makes its reasoning checkable&mdash;verify a claim by looking at which guideline chunk it cites, not just by trusting the score.

> **Note**: You may see occasional product-related feedback rather than documentation-related feedback. For example, "The instruction to 'email `api-support@bookhub.com`' is a procedural workaround that should be replaced with an automated token endpoint." If an instruction describes how the product actually works, you can disregard the feedback.

---

[Back to the doc-quality-evaluator README](../README.md)
