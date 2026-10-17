# Editorial advisor

`editorial_advisor.suggest_edit()` asks a Weights & Biases serverless model which of the
already-retrieved candidate clips fits which shot request, and in what order. It is the
application's own reasoning step: everything else in ClipScout reads the provided VSS
pipeline, this call is ours.

**It advises. It never approves.** `review_required` is always `true`, set by this module
and not by the model.

## Interface

```python
from editorial_advisor import suggest_edit, AdvisorError

advice = suggest_edit(brief, requests, candidates)
```

| Argument | Shape |
| --- | --- |
| `brief` | `str` — the producer's story brief. Untrusted text |
| `requests` | `list[dict]` with `id`, `label`, `query` |
| `candidates` | `list[dict]` with `id`, `request_id`, `reason`, `camera`, `location`, `in`, `out` |

Every `candidate["id"]` must already exist in ClipScout's server catalog. This module never
creates an id and never reaches the archive.

### Returns

```json
{
  "suggestions": [
    {"request_id": "cyclist", "candidate_id": "aaa111", "why": "Short evidence-based rationale"}
  ],
  "potential_gaps": [
    {"request_id": "crossing", "why": "No supplied candidate was recommended for this request"}
  ],
  "proposed_order": ["aaa111"],
  "review_required": true,
  "provider": "wandb",
  "model": "meta-llama/Llama-3.1-8B-Instruct",
  "inference_called": true
}
```

`inference_called` is an addition to the agreed contract. It is `false` only when the
candidate list was empty and no model call was made, so the caller can never present a
no-op as a model result. The six contracted keys are unchanged.

A `potential_gap` means *none of the candidates supplied in this call fit*. It says nothing
about the rest of the archive.

### Raises

`AdvisorError` when the key is missing, the endpoint is unreachable, the call times out, or
the response cannot be read. Its message is safe to show a user and contains no credential,
header or URL.

**There is no fallback.** A failed call raises; it never returns locally-composed text
dressed as model output. Callers should surface the error and leave the editor's existing
candidate list untouched.

## Environment

| Variable | Required | Default |
| --- | --- | --- |
| `WANDB_API_KEY` | **yes** | — |
| `WANDB_INFERENCE_MODEL` | no | `meta-llama/Llama-3.1-8B-Instruct` |
| `WANDB_INFERENCE_BASE_URL` | no | `https://api.inference.wandb.ai/v1` |
| `WANDB_INFERENCE_PROJECT` | no | unset; sent as `OpenAI-Project` for usage tracking |

Base URL and the example model ID were read from the official docs on 17 October 2026
(`docs.wandb.ai/inference`, which now redirects to `docs.coreweave.com/inference`). The
docs list only that one model inline and point elsewhere for the full catalogue, so the
model is overridable. **Confirm the model ID against the live account before the demo.**

Standard library only — `urllib`. No new container dependency.

## Why validation, not prompting, is the boundary

Two inputs are outside our control: the producer's brief, and `reason`, which is a
machine-written caption of archive footage. Either could contain text shaped like an
instruction.

The system prompt does tell the model to treat those blocks as data. That is a courtesy,
not a control. The actual guarantee is structural, applied to the response after it
returns:

- a `candidate_id` not in the supplied candidates is dropped
- a candidate suggested under a `request_id` it does not belong to is dropped
- a `request_id` not in the supplied requests is dropped from gaps
- `proposed_order` is filtered to surviving suggestions, de-duplicated, capped at 12
- any request left without a surviving suggestion is reported as a gap
- `review_required` is overwritten to `true`; extra keys the model invents are discarded

So the worst a fully-steered model can do is return nothing useful. It cannot name footage
the catalog does not hold, move a clip to a request it was not retrieved for, or mark
anything approved. `test_caption_text_cannot_steer_the_output` covers exactly this.

## Tests

```bash
python -m unittest test_editorial_advisor -v
```

19 tests, no network. They cover invented candidate IDs, wrong candidate-to-request
mapping, unknown request IDs in gaps, duplicate sequence entries, the 12-clip cap, empty
candidates, orphan candidates, malformed JSON, fenced JSON, a model trying to set
`review_required: false`, caption-borne prompt injection, missing credentials, timeout,
the absence of a fallback, the API key never appearing in an error message, and the
request targeting the documented endpoint with the documented auth header.

## Integration notes for Track A

- Call it server-side after a search, with candidates taken from the existing catalog.
- Render `suggestions` and `potential_gaps` as advice next to the candidates. Do not let
  it tick the editor's review checkbox or move a clip into the cut.
- `proposed_order` is a proposal for the sequence, not a committed order.
- Catch `AdvisorError` and show its message; the desk must stay usable without it.
- The module needs `WANDB_API_KEY` in the app deployment's secret. Nothing else changes.

## Live verification

**Pending — Track A will run it.** This module was built without lab credentials, so no
real inference request has been made from here. Every test uses an injected transport or a
patched `urlopen`. Until Codex runs one real call against the lab environment, the W&B
integration should be described as implemented and tested, not as verified in production.
