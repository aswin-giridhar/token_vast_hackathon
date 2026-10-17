"""Execute only the exact reviewed batch; preserve job IDs to avoid duplicate starts."""
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT=Path(__file__).parent/'reingest-plan'
PLAN=json.loads((ROOT/'editorial-reingest-plan.json').read_text())
BASE=os.environ['INGRESS_URL'].rstrip('/')
TOKEN=None
STATE=ROOT/'reingest-jobs.json'
QUERIES=['An eye-level tracking shot from a bicycle following a cyclist',
         'A static wide shot of pedestrians crossing a marked street intersection',
         'A high-angle wide shot of moving traffic on a highway']

def api(path,body=None,retry=True):
    global TOKEN
    if TOKEN is None:
        req=Request(BASE+'/api/v1/auth/login',headers={'Content-Type':'application/json'},
            data=json.dumps({'username':os.environ['USERNAME'],'password':os.environ['PASSWORD']}).encode())
        with urlopen(req,timeout=60) as r:TOKEN=json.load(r)['access_token']
    req=Request(BASE+path,headers={'Content-Type':'application/json','Authorization':'Bearer '+TOKEN},
        data=None if body is None else json.dumps(body).encode())
    try:
        with urlopen(req,timeout=90) as r:return json.load(r)
    except HTTPError as e:
        if e.code==401 and retry:
            TOKEN=None
            return api(path,body,False)
        detail=json.loads(e.read().decode()).get('detail')
        if isinstance(detail,list):detail=[{k:x.get(k) for k in ['loc','msg','type']} for x in detail]
        print(json.dumps({'path':path,'http_status':e.code,'detail':detail}),flush=True)
        raise

def snapshot(name):
    results=[]
    for query in QUERIES:
        data=api('/api/v1/search',{'query':query,'top_k':5,'llm_top_n':1,'min_similarity':0.3,'include_public':True})
        results.append({'query':query,'results':[{k:r.get(k) for k in [
            'source','original_video','segment_start_sec','segment_end_sec','similarity_score',
            'reasoning_content','camera_id','location']} for r in data.get('results',[])],
            'relevance_labels':None,'precision_at_5':None})
    (ROOT/name).write_text(json.dumps(results,indent=2),encoding='utf-8')

def main():
    assert os.environ['USERNAME']=='team-32'
    assert PLAN.get('status') == 'approved', 'Review the exact plan and record explicit approval before submitting'
    assert PLAN['total_chunks']==10 and PLAN['total_segments']==60
    assert len(PLAN['requests'])==10 and PLAN['prompt_characters']<=800
    assert all(set(r)=={'original_video','chunk_count','custom_prompt'} and r['chunk_count']==1 for r in PLAN['requests'])
    jobs=json.loads(STATE.read_text()) if STATE.exists() else []
    if not (ROOT/'editorial-search-before.json').exists():snapshot('editorial-search-before.json')
    before=api('/api/v1/dashboard/stats?scope=all')
    if not (ROOT/'dashboard-before.json').exists():
        (ROOT/'dashboard-before.json').write_text(json.dumps({'overview':before.get('overview'),
            'pipeline_alignment':before.get('pipeline_alignment')},indent=2))
    for request in PLAN['requests']:
        if any(j['original_video']==request['original_video'] for j in jobs):continue
        # Record intent before the mutation. An interrupted outcome must be inspected, not retried.
        entry={'original_video':request['original_video'],'status':'submission_pending'}
        jobs.append(entry);STATE.write_text(json.dumps(jobs,indent=2))
        response=api('/api/v1/dashboard/reingest',request)
        entry.update(response)
        STATE.write_text(json.dumps(jobs,indent=2))
        print(json.dumps({'stage':'submitted','number':len(jobs),'job_id':entry.get('job_id'),
            'selected_chunks':entry.get('selected_chunks'),'copied_segments':entry.get('copied_segments')}),flush=True)
    deadline=time.monotonic()+1800
    last=None
    while time.monotonic()<deadline:
        for job in jobs:
            if job.get('status') in ('completed','failed','error','progress_record_lost'):continue
            if not job.get('job_id'):
                raise RuntimeError('Submission outcome needs inspection; no blind retry')
            try:job.update(api('/api/v1/dashboard/reingest/'+job['job_id']))
            except HTTPError as e:
                if e.code==404:job['status']='progress_record_lost'
                else:raise
        STATE.write_text(json.dumps(jobs,indent=2))
        summary=[{k:j.get(k) for k in ['job_id','status','completed_chunks','total_chunks','indexed_segments','total_segments']} for j in jobs]
        text=json.dumps(summary)
        if text!=last:
            print(text,flush=True);last=text
        if all(j.get('status')=='completed' for j in jobs):
            snapshot('editorial-search-after.json')
            stats=api('/api/v1/dashboard/stats?scope=all')
            (ROOT/'dashboard-after.json').write_text(json.dumps({'overview':stats.get('overview'),
                'pipeline_alignment':stats.get('pipeline_alignment')},indent=2))
            print(json.dumps({'stage':'all_completed','overview':stats.get('overview'),
                'pipeline_alignment':stats.get('pipeline_alignment')}),flush=True)
            return
        if all(j.get('status') in ('completed','failed','error','progress_record_lost') for j in jobs):
            raise RuntimeError('One or more jobs did not report completion')
        time.sleep(4)
    print(json.dumps({'stage':'monitor_timeout','job_ids':[j.get('job_id') for j in jobs]}),flush=True)

if __name__=='__main__':
    try:main()
    except Exception as e:
        print(json.dumps({'stage':'error','error_type':type(e).__name__}),flush=True)
        raise SystemExit(1)
