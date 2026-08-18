# Supported formats

This page lists the file formats the evaluator reads, how each is preprocessed before evaluation, and how to declare a document's type so it's graded against the right checklist.

* Markdown (`.md`): fully supported and tested
* MDX (`.mdx`): fully supported and tested
* OpenAPI YAML (`.yaml`, `.yml`): supported by the `RAG-enhanced` evaluator and the batch and CI runners

> **Note**: The evaluator reads plain text files. Other plain text formats, such as `.txt`, may work but have not been tested. Binary formats such as `.docx` are not supported.

## MDX handling

The evaluator preprocesses `.mdx` files before evaluation. The following MDX-specific syntax is stripped:

* YAML frontmatter (the `---` block at the top of the file)
* `import` statements
* JSX component tags, such as `<Note>`, `<Warning>`, and `<CodeGroup>`
* MDX expression comments, such as `{/* comment */}`

Content inside JSX components is preserved &mdash; only the tags are removed. For example, the text inside a `<Note>` block is still evaluated.

> **Important**: The evaluation reflects content quality, not MDX component rendering. Point the evaluator at your docs repository directly &mdash; files are read wherever they live. If you do copy a file into `samples/`, treat the copy as an evaluation input and never as a source of truth: edit the original and re-copy, so a fix can't be stranded in a scratch file.

## OpenAPI YAML handling

YAML files must be OpenAPI or Swagger specifications &mdash; the loader parses the file and rejects it with a clear error if it isn't valid YAML or has no top-level `openapi` or `swagger` key. Specs are evaluated as `docType: reference`, the Diátaxis type whose checklist covers parameters, responses, and error codes.

How a rejection is reported depends on how the batch runner found the file: a non-spec YAML discovered by folder recursion is skipped as "not an OpenAPI spec" (docs repos routinely contain configuration YAML), while a non-spec YAML you name explicitly is reported as an error.

The evaluation prompt tells the model to grade the human-readable content of the spec &mdash; `summary`, `description`, parameter and response documentation, and examples &mdash; and not to penalize Structure for the spec-mandated YAML layout (`paths`, `components`, and so on). The raw YAML text is what gets evaluated, so feedback can reference the exact fields you see in your editor.

YAML files have no frontmatter, so `docType` and `skip-evaluation` don't apply to them. See `samples/books-api.yaml` for a working example.

## Classifying documents with `docType`

The `RAG-enhanced` evaluator reads a `docType` field from a document's frontmatter and uses it to ground the Structure and Completeness criteria in the matching Diátaxis checklist &mdash; instead of asking the model to infer the type from content alone.

Use one of six values: `tutorial`, `how-to`, `reference`, `explanation`, `overview`, or `integration-guide`. `overview` is a practical addition beyond strict Diátaxis, for navigational index or hub pages. `integration-guide` is a how-to specialization for implementation walkthroughs with code and a testing step&mdash;it's scored structurally as `how-to`, but additionally grounds Completeness against Integration Guide Standards (including error-handling guidance), which plain how-to guides aren't held to.

```yaml
---
docType: overview
---
```

When a `docType` is declared, `build_index.py` guarantees that type's own guideline chunk from `diataxis_types.md` is retrieved, regardless of how semantic similarity ranks it against the document being evaluated. See [Retrieval diagnostics](how-it-works.md#retrieval-diagnostics) for what this looks like in the console output.

If `docType` is omitted, the evaluator falls back to inferring the type from the document's content pattern. This is less reliable &mdash; for example, an overview page that lists endpoints and status codes can read enough like a Reference doc that the evaluator scores it against Reference completeness requirements instead of Overview requirements.

This applies to both `.md` and `.mdx` files, not just MDX.

> **Important**: Frontmatter delimiters must be exactly `---` (three hyphens) on their own line, both opening and closing, with nothing before the first one. A missing or malformed delimiter causes `docType` &mdash; and every other frontmatter field &mdash; to be silently ignored; no error is raised. Confirm it worked by checking that the `Evaluating: <path>` console line shows `(docType: <value>)`. If it doesn't, the frontmatter isn't being parsed.

---

[Back to the doc-quality-evaluator README](../README.md)
