# ClipScout: two-agent finish plan

Deadline: **17 October 2026, 16:30 BST**, per the [official event page](https://tokensand.com/vastlondon). Codex remains PM and release owner. The second agent works in SpaceXAI/Cursor, as named on the event page.

## Track A — Codex: working product, integration and delivery

Owner: the existing Codex session.

1. Protect the real VSS search → source review → ordered cut → MP4 + source-list flow. Investigate intermittent upstream search timeouts and verify the final download behavior. Keep the explicit scene-gap branch.
2. Remain the **only re-ingest operator**. Ten approved requests have already copied 60 segments, but indexing is stalled. Preserve job IDs and diagnose/escalate event delivery; never submit that batch again without resolving the original outcome. The demo must work with the existing index.
3. Integrate Track B's isolated W&B module into the server and UI. Keep secrets server-side, add only required secret variables to this app's deployment, and run one real inference request. Show its result as editorial advice requiring review; do not auto-approve footage.
4. Validate source IDs, timecodes, cut order, scene gaps, export duration and decode. Complete a small visual relevance evaluation using the actual clips and the fixed three-query/top-five set. Report the measured score only after labels exist; do not claim a before/after improvement while re-ingest is unfinished.
5. Deploy the final build, merge the reviewed contribution, push to GitHub and assemble submission evidence: a screenshot, a short walkthrough/demo recording with a shareable link, product description and tools-used list. The existing 15-second output montage is product evidence, **not** the required walkthrough recording.

Codex owns `main.py`, `index.html`, `deploy.sh`, `test_main.py`, release documentation and the lab deployment. No replay timeline, simulated dispatch or new live-feed work.

Done when: another teammate can open the deployed app, follow the brief-to-cut flow, download the MP4 and source list, see a real W&B-generated recommendation, and access the repository and demo evidence.

## Track B — SpaceXAI/Cursor agent: W&B editorial advice and evidence

Owner: the second agent, launched by the user. Use a separate clone/branch from current `main`; do not edit the live Codex working directory.

**First deliverable, within about 25 minutes:** one small server-side Python module using the event's Weights & Biases serverless inference endpoint. This is useful work that demonstrates both the coding tool's contribution and an application-level inference call.

Files this agent owns:

- `editorial_advisor.py`
- `test_editorial_advisor.py`
- `docs/EDITORIAL_ADVISOR.md`
- `docs/SPONSOR_EVIDENCE.md`

No changes to `main.py`, `index.html`, `deploy.sh`, ingestion tools, Kubernetes resources or existing source metadata. Codex will wire the module into the app.

### Integration contract

```python
def suggest_edit(brief: str, requests: list[dict], candidates: list[dict]) -> dict:
    ...
```

Input request: `id`, `label`, `query`.

Input candidate: `id`, `request_id`, `reason` (the AI-generated source description), `camera`, `location`, `in`, `out`. The candidate ID must already exist in ClipScout's server catalog. These are candidate descriptions, not verified visual ground truth.

Return a JSON-serializable dictionary:

```json
{
  "suggestions": [
    {"request_id": "cyclist", "candidate_id": "existing-id", "why": "Short evidence-based editorial rationale"}
  ],
  "potential_gaps": [
    {"request_id": "finish", "why": "The supplied candidates do not establish a marathon finish"}
  ],
  "proposed_order": ["existing-id"],
  "review_required": true,
  "provider": "wandb",
  "model": "actual configured model ID"
}
```

Validate all IDs against the supplied inputs and candidate-to-request mapping. Reject malformed output and invented IDs. Remove duplicate sequence IDs. Limit the sequence to 12 clips. An empty candidate list must not produce invented footage. A potential gap refers only to the supplied candidates, not the entire archive.

Use `WANDB_API_KEY` from environment; confirm the current API/base URL and model using the [official inference documentation](https://docs.wandb.ai/inference). Prefer Python standard-library HTTP so the current container stays small. Document any additional non-secret environment settings. Bound network calls with a timeout and return/raise a clear sanitized failure; never label a static fallback as a successful AI response. Treat the brief and captions as untrusted data, not instructions to execute tools. Do not log credentials, raw headers or token-bearing URLs.

Test useful failure modes: unknown candidate IDs, wrong request mapping, malformed JSON, missing credentials, timeout and empty candidates. Record one real inference request only if the agent already has authorized access to the lab environment. Otherwise explicitly mark **live verification pending — Codex will run it**. Never ask for a key in chat, commit one or copy the team's config into the repository.

**Second deliverable, after the module is ready:** a concise sponsor/evidence table with tool, actual contribution, evidence artifact and verification status. Include the SpaceXAI/Cursor contribution's real commit. Distinguish the provided NVIDIA/VAST/CoreWeave pipeline from our new W&B call. Do not claim seven tools, successful re-ingest, a live trigger or precision improvements without proof.

Push the branch and open a PR if the agent has repository write access. Otherwise provide a patch. Send the user the commit/PR URL, test results, exact module signature, required environment variable names and whether a live call succeeded. Do not merge or deploy; Codex owns integration.

## Requirement and evidence checklist

| Item | Current evidence/status | Owner |
| --- | --- | --- |
| Specific video use case | Story brief → reviewed rough cut | A |
| Provided video stack | Real VSS searches and source footage; NVIDIA/VAST-backed index | A |
| Application-level W&B inference | Missing; Track B supplies module, Track A verifies live integration | B → A |
| SpaceXAI/Cursor contribution | Pending actual work and commit from second agent | B |
| Working deployment | Team app is deployed; final regression/download check remains | A |
| Source provenance and gaps | Source timecodes/list; explicit gap keeps request open | A |
| Technical quality/evaluation | Three evidence tests and render measurements pass; relevance labels pending | A; B tests its module |
| Accessible GitHub repository | Public repository and code pushed | A |
| Short demo video, shareable link | Still needed; output montage alone is insufficient | A + team |
| Tools-used description | Existing truthful README; add verified W&B and Cursor evidence | B → A |
| Team names/contact emails | Team must provide and verify these at submission | Team |
| Final submission | Form requires sign-in; not submitted | Team, assisted by A |

The team's earlier brief says **at least three sponsor tools**. Treat that as a target, but confirm how the organizers count tools; the public event page checked today lists partners without that numerical rule. A meaningful Cursor contribution plus the verified W&B integration complements the existing VAST/NVIDIA usage. Opening an agent or naming a sponsor alone is not proof of use.

The public event brief allows search, questions, event spotting **or** actions. It does not require every project to demonstrate live-camera ingestion. Keep the archive scope explicit.

Sources: [official event and deliverables](https://tokensand.com/vastlondon), [official workshop guide, LLM access](https://github.com/vast-data/vast-builders-challenge#llm-access). The submission form is behind sign-in; any additional fields must be checked there before submission.

## Copy this to the second agent

> Work on Track B in `docs/AGENT_SPLIT.md` in https://github.com/aswin-giridhar/token_vast_hackathon. Use a separate branch from current main. Build the W&B editorial-advice module and its meaningful tests first, then the sponsor-evidence note. Keep the exact `suggest_edit` interface and output contract. Edit only the four Track B files. Codex owns the web UI, server integration, deployment, MP4 export and all re-ingest operations. Do not start ingestion, redeploy anything, merge your branch or expose credentials. Return a PR/patch, test results, environment-variable names and honest live-verification status. Aim to hand over the module within 25 minutes; keep the existing demo usable throughout.
