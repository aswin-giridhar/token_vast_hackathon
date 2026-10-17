# Team handoff

## Two-minute demo

1. Explain the problem: finding a clip is only part of editing; the producer needs a usable sequence and its source references.
2. Show **Urban movement** and its three shot requests.
3. Search, open one candidate, inspect the source timecodes and approve it. Show that the coverage board updates only after review.
4. Show a request for which candidates are unsuitable and use **None fit — mark a scene gap**. Keep the editorial gap visible.
5. Open **Your first cut**, show the reviewed order and export the MP4. Download the source shot list with it.
6. Close with: **“ClipScout returns an editable first cut with source references, not just a list of search results.”** The demonstration uses indexed archive footage; do not describe it as live capture.

## Editorial re-ingest

The approved batch consists of ten specific complete parent chunks, six five-second segments per chunk: **60 segments / 300 seconds**. Codex is the single operator. Requests use the exact parent `original_video`, `chunk_count: 1`, and a custom editorial prompt. Camera, capture type and location overrides are omitted to preserve original metadata.

The exact batch manifest and job IDs remain in the operator's local/VM `reingest-plan/` directory, outside Git. Never launch a second operator or rerun preparation over an active batch.

For a future reviewed batch, the helper sequence is:

```bash
# On the lab VM, import the existing team's environment without printing it.
set -a
source /config/team-32.config
set +a

python3 tools/render_spike.py
python3 tools/prepare_reingest.py
# Review tools/reingest-plan/editorial-reingest-review.html and its exact JSON plan.
# Only after explicit approval, set that plan's status to "approved".
python3 tools/run_reingest.py
python3 tools/verify_reingest.py
```

`run_reingest.py` records submission intent before each mutation and saves returned destination URIs. An unknown outcome must be investigated, never blindly resubmitted. A progress endpoint returning 404 does not prove the pipeline failed: the backend's progress registry is process-local. `verify_reingest.py` compares those exact destination URIs against the indexed Explore view and checks camera/location/capture metadata.

Completion requires all **60/60** destination segments indexed, expected metadata retained, and descriptions inspected for the requested editorial attributes. The existing source slots should be replaced without duplicate segment slots. A successful submission response alone is not completion.

**Batch status at the Track A check, 17 October 2026:** all ten requests were accepted. The exact destination URI check now finds **41/60 in the indexed Explore view**, with metadata preserved for the matching rows. None of those descriptions contains the requested explicit `shot type` label, so prompt application is still unverified. The dashboard still reports 60 pending segments and zero re-ingest rows, which conflicts with the source-level check. The process-local progress API previously returned 404. Do not declare success from these conflicting signals and do not submit the batch again. The app demo uses the working existing index and does not depend on this enhancement completing.

The 707-character prompt asks for observable subjects/actions, shot type, camera angle, framing, camera motion, subject motion, obstructions and useful action beats. It prohibits invented identities, emotions, intent, speech and unseen events. See the `PROMPT` constant in `tools/prepare_reingest.py` for its exact text.

## Evaluation

The helpers capture top-five results for fixed editorial queries before and after re-ingest. Label each result against the complete request by watching the footage, including camera motion. Use binary relevance; do not use the AI caption or similarity score as ground truth.

`precision@5 = relevant results among the first five / 5`

Use the same queries, ranking parameters and reviewer rubric for both runs. Keep fewer-than-five results explicit. The basic three-query baseline now has 15 assistant-reviewed sampled-frame labels: 5/5 relevant for each query. See [EVALUATION.md](EVALUATION.md) for the rubric and substantial limitations. This does not measure improvement or the more demanding editorial-query set. Only five minutes of a much larger archive are being re-described, so global search quality may not move substantially.

## Verification performed

- Evidence tests: parent-relative timecodes remain intact; upload time is not treated as capture time; invalid sources are rejected; a ranked segment is not replaced by a different grouped preview.
- First render gate: three four-second sources, 12.000 seconds, 288 frames, 1280×720 at 24 fps; decode succeeded. Six frames around the cuts were inspected.
- Deployed browser flow: real searches for cyclist, pedestrians and highway traffic; source previews; explicit review; three-shot coverage; sequence reorder and restore; MP4 export.
- Scene-gap check: a marathon finish request produced unsuitable street candidates; marking the gap kept coverage at 3/4 and left the three-shot cut unchanged.
- App render: 15.000 seconds, 360 frames, 1280×720 at 24 fps, H.264, no audio; FFmpeg decode completed without errors.
- Source-list download: both the independent list and rendered-job list downloaded through the Codex browser. Labels, parent-relative source times and cumulative cut times match the three-shot sequence.
- Seven regression tests pass, covering source mapping, background-search reuse/cache/refresh/failure, download attachment and catalog/job restoration.

## Protect before adding scope

Keep the deployed desk, scene-gap branch, MP4 and source shot list working. Add integrations only after verifying the endpoint and its actual behavior. Do not spend the demo budget building replay or simulated crew assignments.
