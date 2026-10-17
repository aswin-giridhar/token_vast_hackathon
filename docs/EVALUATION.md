# Small visual relevance baseline

The frozen pre-reingest VSS results contain five segments for each of the three starter queries. Codex inspected five temporally ordered frames per segment (approximately 0.1, 1.1, 2.1, 3.1 and 4.1 seconds). Labels are based on visible content and movement between frames, not generated captions or similarity scores.

| Shot request | Relevant / returned | Precision@5 |
| --- | --- | --- |
| A cyclist riding through a city street | 5 / 5 | 1.00 |
| Pedestrians crossing a street at a crosswalk | 5 / 5 | 1.00 |
| A wide view of moving traffic on a highway | 5 / 5 | 1.00 |

The complete rubric, source IDs, parent-relative timecodes and per-result notes are in [relevance-baseline.json](relevance-baseline.json). The local contact sheets and media remain outside the public repository.

These are **assistant-reviewed sampled-frame labels**, with independent human review pending. Three broad demo-selected queries and 15 results are a smoke test, not a held-out benchmark. Several results come from the same recording or location. Relevance does not establish shot variety, suitability for every brief or real-world production quality. The raw top-five set also differs from the UI's parent-diversified top-six display.

No before/after improvement is claimed. Editorial re-ingest must finish and its prompt application must be verified before comparing another run using the same queries and rubric.

## Reproduce the frame evidence

On the authorized lab VM, load its existing environment, then run:

```bash
python tools/prepare_visual_eval.py /path/to/precision-at-5-review.json /path/to/local-evidence
```

This only reads existing archive media. It does not upload, ingest or alter the index. Each `frames-NN.png` contains five sampled frames in chronological order. Watch the complete segment before making a final editorial approval.
