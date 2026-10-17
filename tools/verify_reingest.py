"""Read-only verification of a submitted batch using the indexed Explore view."""
import json
from pathlib import Path
from urllib.parse import urlencode
import run_reingest as runner

root = Path(__file__).parent / 'reingest-plan'
jobs = json.loads((root / 'reingest-jobs.json').read_text())
plan = json.loads((root / 'editorial-reingest-plan.json').read_text())
inventory = []
offset = 0
while True:
    page = runner.api('/api/v1/videos/explore?' + urlencode({'scope':'all','limit':100,'offset':offset}))
    rows = page.get('videos') or page.get('results') or page.get('items') or page.get('chunks') or []
    inventory.extend(rows)
    if not rows or len(inventory) >= page.get('total',len(inventory)):
        break
    offset += 100
indexed = {s['source']: (row, s) for row in inventory for s in row.get('timeline', [])}
report = []
for job, before in zip(jobs, plan['chunks']):
    matches = [indexed[s] for s in job['destination_sources'] if s in indexed]
    metadata_ok = all(all(row.get(k) == before.get(k) for k in ('camera_id','capture_type','location')) for row, _ in matches)
    descriptions = [str(segment.get('reasoning_content') or '') for _, segment in matches]
    report.append({'job_id':job['job_id'], 'original_video':job['original_video'],
        'expected':len(job['destination_sources']), 'indexed':len(matches),
        'metadata_preserved':metadata_ok if matches else None,
        'editorial_label_count':sum('shot type' in t.lower() for t in descriptions),
        'descriptions':descriptions})
stats = runner.api('/api/v1/dashboard/stats?scope=all')
output = {'chunks':report, 'total_indexed':sum(r['indexed'] for r in report),
    'overview':stats.get('overview'), 'pipeline_alignment':stats.get('pipeline_alignment')}
(root/'verified-progress.json').write_text(json.dumps(output,indent=2))
print(json.dumps({k:v for k,v in output.items() if k!='chunks'}))
print(json.dumps([{k:v for k,v in r.items() if k not in ('descriptions','original_video')} for r in report]))
if output['total_indexed'] == 60:
    runner.snapshot('editorial-search-after.json')
    (root/'dashboard-after.json').write_text(json.dumps({k:v for k,v in output.items() if k in ('overview','pipeline_alignment')},indent=2))
