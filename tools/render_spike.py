"""Gate 1: freeze three real VSS sources, probe, normalize, render and inspect."""
import csv
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent / 'render-proof'
ROOT.mkdir(exist_ok=True)
BASE = os.environ['INGRESS_URL'].rstrip('/')
TOKEN = None


def api(path, payload=None):
    headers = {'Content-Type': 'application/json'}
    if TOKEN:
        headers['Authorization'] = 'Bearer ' + TOKEN
    request = Request(BASE + path, headers=headers,
                      data=None if payload is None else json.dumps(payload).encode())
    with urlopen(request, timeout=90) as response:
        return json.load(response)


def run(args):
    result = subprocess.run(args, capture_output=True, timeout=180)
    if result.returncode:
        # Commands have local media filenames only; never include token URLs.
        raise RuntimeError(result.stderr.decode(errors='replace')[-1800:])
    return result.stdout


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                          '-of', 'json', str(path)]))


def main():
    global TOKEN
    started = time.monotonic()
    TOKEN = api('/api/v1/auth/login', {'username': os.environ['USERNAME'],
                                      'password': os.environ['PASSWORD']})['access_token']
    requests = [
        ('Cyclist', 'A cyclist riding through a city street'),
        ('Crossing', 'Pedestrians crossing a street at a crosswalk'),
        ('Traffic', 'A wide view of moving traffic on a highway'),
    ]
    manifest_path = ROOT / 'frozen-three-clips.json'
    evaluation = []
    if manifest_path.exists():
        shots = json.loads(manifest_path.read_text())
    else:
        shots = []
        for label, query in requests:
            result = api('/api/v1/search', {'query': query, 'top_k': 5,
                'llm_top_n': 1, 'min_similarity': 0.3, 'include_public': True})
            rows = result.get('results', [])
            for rank, row in enumerate(rows, 1):
                evaluation.append({'query': query, 'rank': rank, 'source': row.get('source'),
                    'parent': row.get('original_video'), 'source_in_sec': row.get('segment_start_sec'),
                    'source_out_sec': row.get('segment_end_sec'), 'similarity': row.get('similarity_score'),
                    'description': row.get('reasoning_content'), 'relevant': None,
                    'review_note': ''})
            chosen = next((r for r in rows if r.get('source') and
                           float(r.get('duration') or 0) >= 4), None)
            if chosen is None:
                raise RuntimeError('No usable clip found for ' + label)
            in_sec = float(chosen.get('segment_start_sec') or 0)
            shots.append({'order': len(shots) + 1, 'beat': label, 'query': query,
                'source': chosen['source'], 'original_video': chosen.get('original_video'),
                'camera': chosen.get('camera_id'), 'location': chosen.get('location'),
                'source_in_sec': in_sec, 'source_out_sec': in_sec + 4,
                'segment_local_in_sec': 0, 'duration_sec': 4,
                'description': chosen.get('reasoning_content'), 'audio_mode': 'silent'})
        manifest_path.write_text(json.dumps(shots, indent=2), encoding='utf-8')
        (ROOT / 'precision-at-5-review.json').write_text(json.dumps(evaluation, indent=2), encoding='utf-8')
    print(json.dumps({'stage': 'sources_frozen', 'shots': [
        {k: s[k] for k in ['order', 'beat', 'camera', 'location', 'source_in_sec', 'source_out_sec']} for s in shots]}), flush=True)
    sources, normalized = [], []
    for shot in shots:
        i = shot['order']
        source = ROOT / f'source-{i}.mp4'
        if not source.exists():
            url = BASE + '/api/v1/videos/stream?' + urlencode({'source': shot['source'], 'token': TOKEN})
            with urlopen(url, timeout=90) as response, source.open('wb') as output:
                size = 0
                while block := response.read(1024 * 1024):
                    size += len(block)
                    if size > 150 * 1024 * 1024:
                        raise RuntimeError('Source exceeds spike size limit')
                    output.write(block)
        info = probe(source)
        sources.append({'order': i, 'streams': [{'type': s['codec_type'],
            'codec': s.get('codec_name'), 'width': s.get('width'), 'height': s.get('height'),
            'fps': s.get('avg_frame_rate')} for s in info['streams']],
            'duration': info['format'].get('duration')})
        target = ROOT / f'normalized-{i}.mp4'
        run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
             '-ss', '0', '-i', str(source), '-t', '4', '-map', '0:v:0', '-an',
             '-vf', 'setpts=PTS-STARTPTS,scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24',
             '-frames:v', '96', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
             '-pix_fmt', 'yuv420p', '-video_track_timescale', '24000', str(target)])
        normalized.append(target)
        print(json.dumps({'stage': 'shot_normalized', 'order': i,
            'audio_streams': sum(s['codec_type'] == 'audio' for s in info['streams'])}), flush=True)
    listing = ROOT / 'concat.txt'
    listing.write_text(''.join(f"file '{p.name}'\n" for p in normalized), encoding='utf-8')
    output = ROOT / 'ClipScout_Render_Proof.mp4'
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0',
         '-i', str(listing), '-c', 'copy', '-movflags', '+faststart', str(output)])
    final = probe(output)
    video = next(s for s in final['streams'] if s['codec_type'] == 'video')
    if abs(float(final['format']['duration']) - 12) > 0.05 or int(video['nb_frames']) != 288:
        raise RuntimeError('Output duration/frame-count mismatch')
    run(['ffmpeg', '-v', 'error', '-i', str(output), '-f', 'null', '-'])
    for i, t in enumerate([0.1, 3.9, 4.1, 7.9, 8.1, 11.9], 1):
        run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(t), '-i', str(output),
             '-frames:v', '1', '-vf', 'scale=640:360', '-update', '1', str(ROOT / f'frame-{i}.png')])
    report = {'passed_mechanical_checks': True, 'visual_review': 'pending',
        'sources': sources, 'output': {'duration_sec': float(final['format']['duration']),
            'frames': int(video['nb_frames']), 'fps': video['avg_frame_rate'],
            'width': video['width'], 'height': video['height'], 'audio': 'silent'},
        'render_elapsed_sec': round(time.monotonic()-started, 2)}
    (ROOT / 'render-checks.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    with (ROOT / 'ClipScout_Source_Shot_List.csv').open('w', newline='', encoding='utf-8') as f:
        fields = ['order','beat','camera','location','source','original_video','source_in_sec','source_out_sec','duration_sec']
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader(); writer.writerows(shots)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # HTTP exceptions may carry token-bearing URLs: never print them.
        print(json.dumps({'stage':'failed','error_type':type(error).__name__}), flush=True)
        raise SystemExit(1)
