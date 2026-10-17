"""Read-only inventory and explicit editorial re-ingest request preparation."""
import html
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE=os.environ['INGRESS_URL'].rstrip('/')
TOKEN=None
OUT=Path(__file__).parent/'reingest-plan'
OUT.mkdir(exist_ok=True)
PROMPT=('Describe this clip for a video editor, using only visible evidence. Include: '
    'subjects and observable actions; shot type (establishing/wide/medium/close-up, or unclear); '
    'camera angle (eye-level/high/low/overhead, or unclear); framing and subject position; '
    'camera motion (static/pan/tilt/tracking/handheld, or unclear); subject motion and direction; '
    'useful action beats and visible obstructions, blur or abrupt changes. Preserve the scene context '
    'and concrete searchable details. Distinguish camera movement from subject movement. '
    'Do not invent identity, emotion, intent, location, speech, or events outside the clip. '
    'Use concise natural language with explicit labels for shot type, angle, framing and motion.')

def api(path,payload=None):
    headers={'Content-Type':'application/json'}
    if TOKEN:headers['Authorization']='Bearer '+TOKEN
    with urlopen(Request(BASE+path,headers=headers,data=None if payload is None else json.dumps(payload).encode()),timeout=90) as r:
        return json.load(r)

def main():
    global TOKEN
    TOKEN=api('/api/v1/auth/login',{'username':os.environ['USERNAME'],'password':os.environ['PASSWORD']})['access_token']
    inventory=[]
    offset=0
    while True:
        page=api('/api/v1/videos/explore?'+urlencode({'scope':'all','limit':100,'offset':offset}))
        rows=page.get('videos') or page.get('results') or page.get('items') or page.get('chunks') or []
        if not rows:
            print(json.dumps({'empty_page_keys':list(page),'offset':offset}))
            break
        inventory.extend(rows)
        offset+=100
        if len(inventory)>=page.get('total',len(inventory)):
            break
    complete=[]
    for row in inventory:
        timeline=row.get('timeline') or []
        total=int(row.get('total_segments') or len(timeline))
        if total and set(range(1,total+1)).issubset({int(s.get('segment_number') or 0) for s in timeline}):
            complete.append(row)
    baseline=Path(__file__).parent / 'render-proof' / 'precision-at-5-review.json'
    wanted=[]
    for r in json.loads(baseline.read_text()):
        if r['parent'] not in wanted:wanted.append(r['parent'])
    selected=[]
    by_source={r['original_video']:r for r in complete}
    for source in wanted:
        if source in by_source:selected.append(by_source[source])
        if len(selected)==10:break
    if len(selected)<10:
        eligible=[r for r in complete if r.get('capture_type') in ('streets','traffic')]
        eligible.sort(key=lambda r:(r.get('camera_id',''),r.get('original_video','')))
        used={r['original_video'] for r in selected}
        for row in eligible:
            if row['original_video'] in used:continue
            selected.append(row);used.add(row['original_video'])
            if len(selected)==10:break
    if len(selected)!=10:raise RuntimeError('Could not resolve ten complete chunks')
    fields=['filename','original_video','stream_id','chunk_index','camera_id','capture_type','location','upload_timestamp','ingest_kind','total_segments','chunk_duration_sec']
    summarize=lambda r:{**{k:r.get(k) for k in fields},'indexed_segments':len(r.get('timeline') or []),
        'description':str(r.get('reasoning_content') or ((r.get('timeline') or [{}])[0].get('reasoning_content')) or '')[:500]}
    proposals=[summarize(r) for r in selected]
    config=api('/api/v1/metadata/ingest-config')
    sample=selected[0].get('preview_source') or selected[0]['timeline'][0]['source']
    metadata=api('/api/v1/videos/metadata?'+urlencode({'source':sample}))
    plan={'status':'awaiting_confirmation','prompt':PROMPT,'prompt_characters':len(PROMPT),
        'metadata_policy':'preserve original camera_id, capture_type and location by omitting overrides',
        'current_prompt':'Not exposed by the API; no claim about original prompt text.',
        'chunks':proposals,'total_chunks':len(proposals),'total_segments':sum(r['indexed_segments'] for r in proposals),
        'total_duration_sec':sum(float(r.get('chunk_duration_sec') or 0) for r in proposals),
        'requests':[{'original_video':r['original_video'],'chunk_count':1,'custom_prompt':PROMPT} for r in selected],
        'inventory_total':len(inventory),'complete_inventory_total':len(complete),
        'available_scenarios':config.get('analysis_scenarios'),
        'representative_current_metadata':{k:metadata.get(k) for k in ['camera_id','capture_type','location','upload_timestamp']}}
    (OUT/'editorial-reingest-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    (OUT/'complete-inventory.json').write_text(json.dumps([summarize(r) for r in complete],indent=2),encoding='utf-8')
    def table(rows):
        return '<table><tr><th>Source / stable ID</th><th>Camera / location</th><th>Clips</th><th>Duration</th><th>Ingest metadata</th></tr>'+''.join(
            '<tr><td>'+html.escape(r.get('filename') or '')+'<br><code>'+html.escape(r['original_video'])+'</code></td><td>'+html.escape(str(r.get('camera_id')))+'<br>'+html.escape(str(r.get('location')))+'<br>'+html.escape(str(r.get('capture_type')))+'</td><td>'+str(r['indexed_segments'])+'</td><td>'+str(r.get('chunk_duration_sec'))+'s</td><td>'+html.escape(str(r.get('ingest_kind')))+'<br>'+html.escape(str(r.get('upload_timestamp')))+'<br>stream: '+html.escape(str(r.get('stream_id')))+'</td></tr>' for r in rows)+'</table>'
    doc='<html lang="en"><meta charset="utf-8"><title>ClipScout editorial re-ingest review</title><style>body{font:15px/1.5 Arial;margin:40px;color:#20332d}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:12px;border:1px solid #ddd;text-align:left}code{overflow-wrap:anywhere;font-size:10px}pre{white-space:pre-wrap;background:#edf4ed;padding:20px}h2{margin-top:32px}</style><h1>Editorial re-ingest — request for review</h1><p>Not started. '+str(plan['total_chunks'])+' whole source chunks; '+str(plan['total_segments'])+' indexed short segments; '+str(plan['total_duration_sec'])+' seconds. Preserve existing camera/location/capture metadata.</p><h2>Exact custom prompt</h2><pre>'+html.escape(PROMPT)+'</pre><p>The API does not expose the prior analysis prompt. These requests replace descriptions and embeddings for the selected existing segment slots.</p><h2>Proposed ten chunks</h2>'+table(proposals)+'<details><summary>All '+str(len(complete))+' complete source chunks available for selection</summary>'+table([summarize(r) for r in complete])+'</details></html>'
    (OUT/'editorial-reingest-review.html').write_text(doc,encoding='utf-8')
    print(json.dumps({'plan_path':str(OUT),'total_chunks':plan['total_chunks'],'total_segments':plan['total_segments'],'total_duration_sec':plan['total_duration_sec'],'prompt_characters':len(PROMPT),'inventory_total':len(inventory),'selected':proposals}),flush=True)

if __name__=='__main__':
    try:main()
    except Exception as e:
        print(json.dumps({'status':'failed','error_type':type(e).__name__}),flush=True)
        raise SystemExit(1)
