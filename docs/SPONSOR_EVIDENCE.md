# Sponsor and tool evidence

Written 17 October 2026. Each row says what the tool actually did in this project, what
artifact proves it, and whether that has been verified end to end. Rows are deliberately
conservative: a tool we consumed through the provided application is marked as such rather
than claimed as our own integration.

## What we used

| Tool | Actual contribution | Evidence artifact | Verification |
| --- | --- | --- | --- |
| **VAST Data** | S3 segment storage, VastDB index, DataEngine pipeline. Reached through the provided VSS search, auth, media and dashboard APIs | `main.py` `VSS` class; live searches in the deployed desk; `docs/render-proof.json` sources streamed from the archive | **Verified** — the deployed app runs against the real team-32 index |
| **NVIDIA** | Cosmos Reason wrote the segment descriptions we match and display; Cosmos Embed produced the vectors behind semantic search; YOLO11 produced the detections | `reasoning_content` and `similarity_score` in every search result rendered by `index.html` | **Verified, but consumed indirectly** — these models run inside the supplied pipeline. We query them through VSS; we do not call them ourselves |
| **CoreWeave** | GPUs hosting the NVIDIA models above | No artifact of our own | **Underlying infrastructure.** We did not exercise it separately and do not claim it as a distinct integration |
| **Weights & Biases** | **Our own application-level inference call.** `suggest_edit()` asks a W&B serverless model which retrieved candidates fit which shot request | `editorial_advisor.py`, 20 tests in `test_editorial_advisor.py`, `docs/EDITORIAL_ADVISOR.md`; commit `196102a` | **Implemented and tested; live call pending.** Built without lab credentials — all tests use an injected transport. Track A must run one real request before this is described as working in production |
| **SpaceXAI / Cursor** | Authored the Track B module, its tests and documentation in a separate agent session | Commit `196102a` on branch `track-b-wandb-editorial-advisor` | **Verified** — a real commit with passing tests, not merely an agent being opened |
| **FFmpeg** (not a sponsor) | Normalises and assembles the exported cut | `docs/render-proof.json`: three sources at 1920×1080 / 29.97 and 30 fps normalised to 1280×720 at 24 fps, output 12.000 s / 288 frames, decode clean, six boundary frames inspected | **Verified by measurement** |

## The distinction that matters

Everything in the first three rows is the stack the organisers handed us already running.
We used it properly and the application depends on it, but querying a provided pipeline is
not the same as integrating a tool ourselves.

**The Weights & Biases call is the one piece of model reasoning this team added.** It is
the application deciding something — which clip serves which beat — rather than the
pipeline describing footage. That is the honest claim, and it is the only one we make
about a tool we wired up.

## What we are not claiming

- **Not a successful re-ingest.** Ten approved requests copied 60 segments; **41 of 60 exact destination URIs were found in the indexed view** at the Track A check. Dashboard counts conflict, and the requested editorial labels are absent. Completion and prompt application remain unverified. No job has been resubmitted.
- **Not a precision improvement.** The basic three-query, top-five baseline now has assistant-reviewed sampled-frame labels: 5/5 relevant per query. This is a small demo-selected smoke test with independent human review pending, not a benchmark or a before/after gain. See `docs/EVALUATION.md`.
- **Not a live trigger, live-camera ingestion, replay or crew dispatch.** None of it is
  implemented. The earlier workflow diagram shows these as a proposed product direction,
  not as built features.
- **Not transcription or speech search.** Some archive sources do carry audio tracks, but
  we never tested whether they contain speech and Canary-1B is not wired in. Exports are
  silent by design.
- **Not seven tools.** An earlier internal note counted every component in the stack
  separately. The table above is the count we will stand behind.
- **Not independent W&B video analysis.** The verified application call evaluates the supplied VSS descriptions. Actual source footage still requires editorial review.

## Verification still outstanding

| Item | Owner |
| --- | --- |
| One real W&B inference request from the lab environment | Complete � evidence JSON |
| Wire the advisor into the server and UI as review-required advice | Complete � deployed UI verified; cut/coverage unchanged, review checkbox starts unchecked |
| Complete the three-query relevance labels | Assistant sampled-frame baseline complete; independent human review pending |
| Short walkthrough recording with a shareable link | Team |
| Team names and contact emails on the submission | Team |
