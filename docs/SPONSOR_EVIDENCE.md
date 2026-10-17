# Sponsor and tool evidence

Updated 17 October 2026 after Track B integration. PR #1 was merged as `24e166b`. A name in this table is not a claim that the organizers count it as a separate qualifying tool.

| Tool | Actual contribution | Evidence | Verification |
| --- | --- | --- | --- |
| **VAST Data** | Segment storage, VastDB index and supplied DataEngine pipeline; reached through VSS search, authentication, media and dashboard APIs | `main.py`, deployed source previews, exported source list | Real archive retrieval and media verified |
| **NVIDIA** | Cosmos Reason descriptions and Cosmos Embed vectors in the supplied video pipeline | Search-result descriptions and similarity ranking | Consumed through VSS; we did not deploy these models. The pipeline also includes the separate YOLO11 detector |
| **CoreWeave** | Infrastructure hosting the supplied models and W&B inference | Workshop stack and W&B endpoint | Infrastructure dependency; not claimed as an additional independent integration |
| **Weights & Biases** | Our application asks a serverless model to recommend clips, order and potential gaps from retrieved descriptions | `editorial_advisor.py`, 20 module tests, `docs/wandb-live-verification.json`, deployed advice UI | **Live verified:** 14:11:39 UTC, 1.73 seconds, four requests and three real candidates. UI call also verified; approval remains manual |
| **SpaceXAI / Cursor** | The second agent authored the advisor, its tests and documentation | Commit `196102a`, branch `track-b-wandb-editorial-advisor`, [PR #1](https://github.com/aswin-giridhar/token_vast_hackathon/pull/1) | Contribution merged; Codex reviewed, integrated, tested and deployed it |
| **FFmpeg** (not a sponsor) | Normalize and assemble the selected footage | `docs/render-proof.json`, final render measurements | Final app cut: 15.000 seconds, 360 frames, H.264, 1280x720, 24 fps, silent; decode passed |

The W&B call is the application's own reasoning step. It receives candidate descriptions and metadata, not video bytes. ID validation limits its choices, but a valid ID does not make its rationale correct: the editor still checks the source footage.

## Claims and limits

- **Re-ingest is not declared complete.** Ten approved requests copied 60 segments. A source-level check found 41 exact destination URIs in the indexed view, with preserved metadata, but dashboard counts conflict and explicit editorial labels are absent. No batch was resubmitted.
- **No measured precision improvement.** The basic three-query baseline has assistant-reviewed sampled-frame labels: 5/5 relevant per query. It is a small demo-selected smoke test with independent human review pending. See `docs/EVALUATION.md`.
- **Archive scope.** No live trigger, live-camera ingestion, replay simulation or crew dispatch is implemented. The earlier live-event diagram describes a future product direction.
- **No speech claims.** Some sources contain audio tracks, but there is no transcription or speech search. Exports are silent by design.
- **No seven-tool claim.** We distinguish direct application integrations, coding contributions and dependencies in the supplied stack.

## Delivery evidence

| Item | Status |
| --- | --- |
| Real W&B call and model ID | Verified; evidence JSON committed |
| Advisor in server and UI | Verified; cut/coverage unchanged, review checkbox starts unchecked |
| Automated checks | 29 tests passed |
| Visual relevance baseline | Assistant sampled-frame review complete; independent human review pending |
| Short walkthrough with shareable link | Complete: 79-second annotated demo in `docs/demo/ClipScout_Walkthrough.mp4`; see `docs/SUBMISSION.md` |
| Team names, emails and submission sign-in | Team must supply and verify |
