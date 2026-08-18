# Troubleshooting

Refer to this page if you encounter an error, an unexpected score, or feedback that doesn't match what's in your document.

## Context-blind feedback

The evaluator is unaware of how a document fits into a larger documentation set. It evaluates each file in isolation. Feedback about missing definitions, unexplained terminology, or incomplete scope may reflect content that exists elsewhere in your documentation&mdash;for example, in a top-level README or a linked reference document.

Always apply editorial judgment by considering the context of the entire documentation set, not just individual files, before acting on evaluator feedback.

## FileNotFoundError: [Errno 2] No such file or directory: 'my_doc.md'

The folder and filename are incorrect or missing. Verify that the folder and filename are correct, then try again.

## zsh: command not found: codespell

codespell is installed but its console script isn't on your `PATH`. pip places console scripts in a user directory that many shells don't include by default, and pip prints a warning about this at install time that's easy to miss.

Run it through Python instead, which never depends on `PATH`:

```text
python3 -m codespell_lib
```

If codespell isn't installed at all, `pip install -r requirements.txt` installs it with the other dependencies.

## TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'

Your Python is older than 3.10. The batch runner, the report renderer, and the CI runner use `X | None` type annotations, which Python evaluates when the module is imported, so the error appears immediately rather than when the annotated function runs. Check your version with `python3 --version` and upgrade to 3.10 or later. The `baseline` and `RAG-enhanced` single-file evaluators are unaffected.

## Error: Collection 'doc_guidelines' not found

The evaluator can't find the ChromaDB vector index. Run `python3 build_index.py` to create it, then run the evaluation again. The index is required by `evaluate_rag.py`, `evaluate_batch.py`, and the CI runner; only the `baseline` `evaluate.py` runs without it.

## Error code 400: user messages must have non-empty content

The file the evaluator is pointing to is empty or has no readable content. Open the file in your editor and confirm it contains text. If the file is empty, add content and rerun the evaluator. The batch and CI runners detect these files up front and skip them with a "no evaluable content" note, so this error only occurs with the single-file evaluators (`evaluate.py` and `evaluate_rag.py`). Here's an example of the error message:

```text
anthropic.BadRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'messages.0: user messages must have non-empty content'}, 'request_id': 'req_011CaAADrvnXeUYsBcu8jQW7'}
```

## JSON parse error

If the evaluator can’t parse the model’s response as JSON, it prints the parse error and the raw response for debugging, then exits. This can happen when the response contains unescaped quotes or is truncated. Run the evaluation again&mdash;if the error persists with a long document, the response may exceed the token limit (see `max_tokens` in the script). This applies only to the baseline `evaluate.py`: the RAG evaluator (`evaluate_rag.py`) and the CI runner use structured tool output and do not parse JSON from text, so they are not subject to this error.

## A score column shows `?`, or a criterion's feedback is empty

The evaluator asks the model for an integer score and a feedback sentence per criterion. The model occasionally misfiles one into the other &mdash; putting the feedback sentence in the score field, or leaving the feedback empty. Rather than crashing the run, the renderer shows `?` in place of the missing score and keeps any stray text as that criterion's feedback. A `?` in the console table appears the same way in the Markdown report, both in the score column and as `**Structure (?/5):**` in the feedback block.

This is a model-output glitch, not a problem with your document. The `overall` score is unaffected, so the pass/fail gate still works normally. Rerun the evaluation and the criterion usually scores normally.

## Feedback references broken or unverifiable links

The evaluator cannot click or verify links, so it's penalizing you for not embedding content inline. If the evaluator flags links as broken or unverifiable, manually test the links before making any changes. Use a link checker such as GitHub Actions for automated verification.

## Unicode characters appear in the JSON output

If Unicode characters appear in the JSON output, verify that `ensure_ascii=False` appears in the `evaluate.py` or `evaluate_rag.py` script and try again.

## 0 evaluation score

A zero (`0`) in the evaluation score indicates something went wrong with the evaluation. Here are the scenarios that would trigger a 0:

* **Malformed or empty input file**: If the evaluator reads an empty `.md` file, the model has nothing to evaluate and might return the unfilled template.
* **Prompt misfire**: If the system prompt is truncated or corrupted, the model might return the default structure.
* **Non-doc input**: If someone accidentally points the evaluator at a non-doc file, such as a config file or script, the model might not know how to score it.

---

[Back to the doc-quality-evaluator README](../README.md)
