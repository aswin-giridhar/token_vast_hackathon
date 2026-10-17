"""Read-only: download a frozen result set and extract five frames per segment.

Run on the lab VM with its existing team environment. Output stays outside Git.
Usage: python tools/prepare_visual_eval.py manifest.json output-folder
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def main():
    rows = json.loads(Path(sys.argv[1]).read_text())
    folder = Path(sys.argv[2])
    folder.mkdir(parents=True, exist_ok=True)
    base = os.environ['INGRESS_URL'].rstrip('/')
    req = Request(base + '/api/v1/auth/login',
        data=json.dumps({'username': os.environ['USERNAME'], 'password': os.environ['PASSWORD']}).encode(),
        headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=45) as response:
        token = json.load(response)['access_token']
    for i, row in enumerate(rows, 1):
        source = folder / f'clip-{i:02}.mp4'
        if not source.exists():
            query = urlencode({'source': row['source'], 'token': token})
            try:
                with urlopen(base + '/api/v1/videos/stream?' + query, timeout=90) as response, source.open('wb') as out:
                    total = 0
                    while chunk := response.read(1024 * 1024):
                        total += len(chunk)
                        if total > 150 * 1024 * 1024:
                            raise ValueError('Oversized segment')
                        out.write(chunk)
            except Exception as error:
                source.unlink(missing_ok=True)
                raise RuntimeError('Media retrieval failed: ' + type(error).__name__) from None
        # 0.1, 1.1, 2.1, 3.1 and 4.1 seconds, in temporal order.
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '0.1', '-i', str(source),
            '-vf', 'fps=1,scale=400:225,tile=5x1', '-frames:v', '1', '-update', '1',
            str(folder / f'frames-{i:02}.png')], check=True, timeout=60,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(json.dumps({'completed': i, 'total': len(rows), 'rank': row['rank']}), flush=True)


if __name__ == '__main__':
    main()
