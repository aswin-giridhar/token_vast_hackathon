# ClipScout submission pack

## Links

- Repository: https://github.com/aswin-giridhar/token_vast_hackathon
- App: https://team-32-app.thecosmoslabs.com/app/ (workshop access may be required)
- Demo video: https://github.com/aswin-giridhar/token_vast_hackathon/raw/refs/heads/main/docs/demo/ClipScout_Walkthrough.mp4
- Screenshot: [Integrated editorial advice](demo/ClipScout_Integrated_Advice.png)
- Sponsor evidence: [SPONSOR_EVIDENCE.md](SPONSOR_EVIDENCE.md)
- Evaluation: [EVALUATION.md](EVALUATION.md)
- Merged contribution: https://github.com/aswin-giridhar/token_vast_hackathon/pull/1

The demo is a **79-second annotated walkthrough**, using actual deployed-app screenshots and the actual 15-second exported cut. It is silent, with English explanations on screen. It is not a continuous screen recording. The MP4 is 1920x1080, 24 fps, 1,896 frames; decode and duration checks passed.

## Project description

**ClipScout turns a story brief into a reviewed first cut with source references.** Editors describe the shots they need, search the provided VSS video archive, and preview the original footage. W&B serverless inference recommends candidate clips, a sequence and potential coverage gaps from the retrieved descriptions. The editor verifies each source before approving it, then reorders the selected shots and exports a silent MP4 with a source shot list.

Our demo uses urban archive footage: a cyclist, pedestrians crossing and a wide highway view. A marathon-finish request remains an explicit scene gap, demonstrating that the application does not automatically fill an unsupported story beat. The result is a useful editorial artifact: a first cut and the source IDs, original In/Out points and cut positions needed to trace every chosen shot.

## Tools used

VAST storage, database and the supplied VSS pipeline support real footage retrieval. NVIDIA Cosmos Reason and Cosmos Embed supply descriptions and semantic matching within that pipeline. Our own W&B serverless call performs editorial reasoning. The SpaceXAI/Cursor agent contributed the advisor module, tests and documentation in PR #1; Codex handled the application, review, integration, validation and deployment. FFmpeg normalizes and assembles the exported video. See the sponsor evidence table for the distinction between direct integrations and provided infrastructure.

## Evidence worth mentioning

- 29 automated tests passed, including source provenance, malformed model output, invented IDs, wrong request mapping, inference timeout and missing credentials.
- A real W&B call returned three valid suggestions and one potential gap in 1.73 seconds. This is one observation, not a latency benchmark. The deployed UI call also succeeded.
- Suggestions did not change the approved sequence or coverage; source review opened with its approval checkbox unchecked.
- The final cut is 15.000 seconds, 360 frames, H.264, 1280x720, 24 fps and silent. Decode and six boundary-frame checks passed. Both MP4 and JSON downloads worked in the browser.
- The saved export survived a controlled redeploy with the same SHA-256 hash.
- Fifteen sampled-frame relevance labels support a small basic-query baseline: 5/5 relevant for each of three requests. Independent human review is pending; this is not a general benchmark or an improvement claim.

## Honest limits

This is an archive montage, not live event capture. There is no live trigger, crew dispatch, speech transcription or shared multi-editor draft. W&B assesses supplied descriptions, not video pixels. Application drafts are browser-local. Controlled deployment backs up and restores exports, but uncontrolled pod replacement can still lose newer temporary files.

The ten-chunk editorial re-ingest was submitted once. A direct read-only database check found 41/60 exact destination sources, with no explicit shot-type labels; dashboard counts conflict. Its completion and prompt application remain unverified. The core demo does not depend on it.

## Team's final actions

1. Watch the demo and confirm the project description and tool attribution.
2. Add the team members' real names and contact emails in the organizer's submission form; these are intentionally not invented or published here.
3. Sign in and submit the repository, demo link and description through the event's submission flow. **No final submission has been made by Codex.**

The [official event page](https://tokensand.com/vastlondon) states a **16:30 BST deadline on 17 October 2026** and requests an accessible repository, a short demo with a shareable link, a description/tools list, and team names/contact emails. Check any additional fields in the signed-in submission form.
