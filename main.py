"""ClipScout editorial desk. VSS authentication stays on the server."""
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
DATA = Path(os.environ.get("DATA_DIR", "/tmp/clipscout"))
DATA.mkdir(parents=True, exist_ok=True)
LOG = logging.getLogger("clipscout")
CATALOG = {}
JOBS = {}
LOCK = threading.RLock()
RENDER_LOCK = threading.Lock()


class VSS:
    def __init__(self):
        self.base = os.environ.get("VSS_URL", "").rstrip("/")
        self.token = None
        self.expires = 0
        self.lock = threading.RLock()

    def authenticate(self):
        with self.lock:
            if self.token and time.time() < self.expires:
                return self.token
            body = json.dumps({"username": os.environ["VSS_USERNAME"],
                               "password": os.environ["VSS_PASSWORD"]}).encode()
            req = Request(self.base + "/api/v1/auth/login", data=body,
                          headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=45) as r:
                self.token = json.load(r)["access_token"]
            self.expires = time.time() + 1200
            return self.token

    def call(self, path, payload=None, retry=True):
        token = self.authenticate()
        req = Request(self.base + path,
                      data=None if payload is None else json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
        try:
            with urlopen(req, timeout=90) as r:
                return json.load(r)
        except HTTPError as e:
            if e.code == 401 and retry:
                self.expires = 0
                return self.call(path, payload, False)
            raise

    def media(self, source, range_header=None, retry=True):
        token = self.authenticate()
        query = urlencode({"source": source, "token": token})
        headers = {"Range": range_header} if range_header else {}
        try:
            return urlopen(Request(self.base + "/api/v1/videos/stream?" + query,
                                   headers=headers), timeout=90)
        except HTTPError as e:
            if e.code == 401 and retry:
                self.expires = 0
                return self.media(source, range_header, False)
            raise


vss = VSS()


def normalize(row):
    """Use the actual ranked segment, not a different grouped preview segment."""
    source = row.get("source", "")
    if not isinstance(source, str) or not source.startswith("s3://"):
        return None
    start = float(row.get("segment_start_sec") or 0)
    end = float(row.get("segment_end_sec") or start + float(row.get("duration") or 5))
    if end <= start or end - start > 120:
        return None
    clip = {
        "id": hashlib.sha256(source.encode()).hexdigest()[:24],
        "source": source,
        "original_video": row.get("original_video", source),
        "filename": row.get("filename", source.rsplit("/", 1)[-1]),
        "in": start, "out": end, "duration": end - start,
        "camera": row.get("camera_id") or "Camera not supplied",
        "location": row.get("location") or "Location not supplied",
        "capture_type": row.get("capture_type") or "Unknown",
        "capture_time": None,
        "ingested_at": row.get("upload_timestamp"),
        "reason": str(row.get("reasoning_content") or "No description supplied.")[:6000],
        "similarity": float(row.get("similarity_score") or 0),
        "objects": str(row.get("object_classes") or "").split(",")[:16],
    }
    with LOCK:
        CATALOG[clip["id"]] = clip
        (DATA / "catalog.json").write_text(json.dumps(CATALOG), encoding="utf-8")
    return clip


try:
    CATALOG.update(json.loads((DATA / "catalog.json").read_text(encoding="utf-8")))
except (OSError, ValueError):
    pass


def search(query):
    started = time.monotonic()
    result = vss.call("/api/v1/search", {
        "query": query, "top_k": 15, "llm_top_n": 1,
        "min_similarity": 0.3, "include_public": True,
    })
    clips, seen = [], set()
    for row in result.get("results", []):
        parent = row.get("original_video") or row.get("source")
        if parent in seen:
            continue
        clip = normalize(row)
        if clip:
            clips.append(clip)
            seen.add(parent)
        if len(clips) == 6:
            break
    return {"clips": clips, "query": query,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "summary": (result.get("llm_synthesis") or {}).get("response", ""),
            "mode": "indexed_archive"}


def render(job_id, ids):
    job = JOBS[job_id]
    try:
        job["status"] = "rendering"
        folder = DATA / "renders" / job_id
        folder.mkdir(parents=True)
        files = []
        for i, clip_id in enumerate(ids):
            clip = CATALOG[clip_id]
            original = folder / f"source-{i}.mp4"
            total = 0
            with vss.media(clip["source"]) as response, original.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > 150 * 1024 * 1024:
                        raise ValueError("Clip is too large")
                    output.write(chunk)
            target = folder / f"shot-{i}.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "0", "-i", str(original),
                "-t", str(min(clip["duration"], 30)), "-map", "0:v:0", "-an",
                "-vf", "setpts=PTS-STARTPTS,scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24",
                "-frames:v", str(round(min(clip["duration"], 30) * 24)),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                "-video_track_timescale", "24000", str(target)
            ], check=True, timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            original.unlink()
            files.append(target)
            job["completed"] = i + 1
        listing = folder / "clips.txt"
        listing.write_text("".join(f"file '{p.name}'\n" for p in files), encoding="utf-8")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
                        "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart",
                        str(folder / "clipscout-rough-cut.mp4")],
                       check=True, timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for path in files:
            path.unlink()
        source_list = []
        offset = 0
        for i, clip_id in enumerate(ids, 1):
            clip = CATALOG[clip_id]
            duration = min(clip["duration"], 30)
            source_list.append({"order": i, "source": clip["source"], "original_video": clip["original_video"],
                "camera": clip["camera"], "location": clip["location"], "source_in_sec": clip["in"],
                "source_out_sec": clip["in"] + duration, "cut_in_sec": offset, "cut_out_sec": offset + duration})
            offset += duration
        (folder / "source-shot-list.json").write_text(json.dumps({"audio": "silent", "shots": source_list}, indent=2))
        job["duration_sec"] = offset
        job["status"] = "done"
    except Exception as error:
        job["status"] = "error"
        job["error"] = "Export could not complete. Your reviewed shot list is still available."
        LOG.warning("render failed: %s", type(error).__name__)
    finally:
        RENDER_LOCK.release()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Do not log URLs, request bodies, upstream responses or auth material.
        pass

    def reply(self, status, value):
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def route(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/app":
            path = "/"
        elif path.startswith("/app/"):
            path = path[4:]
        return path, parse_qs(parsed.query)

    def do_GET(self):
        try:
            path, params = self.route()
            if path == "/health":
                return self.reply(200, {"status": "ok", "app": "clipscout", "version": "0.1.0"})
            if path == "/api/status":
                stats = vss.call("/api/v1/dashboard/stats?scope=all")
                return self.reply(200, {"connected": True, "team": os.environ.get("VSS_USERNAME"),
                    "clips": stats.get("overview", {}).get("indexed_clips"),
                    "healthy": stats.get("pipeline_alignment", {}).get("healthy"),
                    "export_available": bool(shutil.which("ffmpeg"))})
            if path == "/api/media":
                clip = CATALOG.get(params.get("id", [""])[0])
                if not clip:
                    return self.reply(404, {"error": "Clip no longer cached. Search again."})
                with vss.media(clip["source"], self.headers.get("Range")) as response:
                    self.send_response(response.status)
                    for name in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
                        if response.headers.get(name):
                            self.send_header(name, response.headers[name])
                    self.send_header("Cache-Control", "private, max-age=300")
                    self.end_headers()
                    shutil.copyfileobj(response, self.wfile, 64 * 1024)
                return
            if path.startswith("/api/jobs/"):
                parts = path.split("/")
                job_id = parts[3]
                job = JOBS.get(job_id)
                if not job:
                    return self.reply(404, {"error": "Export job not found"})
                if len(parts) == 5 and parts[4] == "sources" and job["status"] == "done":
                    source_list = DATA / "renders" / job_id / "source-shot-list.json"
                    return self.reply(200, json.loads(source_list.read_text()))
                if len(parts) == 5 and parts[4] == "download" and job["status"] == "done":
                    target = DATA / "renders" / job_id / "clipscout-rough-cut.mp4"
                    self.send_response(200)
                    self.send_header("Content-Type", "video/mp4")
                    self.send_header("Content-Length", str(target.stat().st_size))
                    self.send_header("Content-Disposition", 'attachment; filename="clipscout-rough-cut.mp4"')
                    self.end_headers()
                    with target.open("rb") as source:
                        shutil.copyfileobj(source, self.wfile)
                    return
                return self.reply(200, job)
            if path in ("/", "/index.html"):
                data = (ROOT / "index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-cache")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(data)
                return
            self.reply(404, {"error": "Not found"})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as error:
            LOG.warning("request failed: %s", type(error).__name__)
            self.reply(502, {"error": "VSS is not responding. Please try again."})

    def do_POST(self):
        try:
            path, _ = self.route()
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                return self.reply(403, {"error": "Cross-origin request rejected"})
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/json":
                return self.reply(415, {"error": "JSON request required"})
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 32000:
                return self.reply(400, {"error": "Invalid request size"})
            payload = json.loads(self.rfile.read(length))
            if path == "/api/search":
                query = str(payload.get("query", "")).strip()
                if not 3 <= len(query) <= 600:
                    return self.reply(400, {"error": "Describe a shot in 3–600 characters."})
                return self.reply(200, search(query))
            if path == "/api/render":
                ids = payload.get("clip_ids")
                if not isinstance(ids, list) or not 1 <= len(ids) <= 12 or any(not isinstance(i, str) or i not in CATALOG for i in ids):
                    return self.reply(400, {"error": "Choose 1–12 cached, reviewed clips. Search again if needed."})
                if not shutil.which("ffmpeg"):
                    return self.reply(503, {"error": "MP4 export is not available yet."})
                if not RENDER_LOCK.acquire(blocking=False):
                    return self.reply(409, {"error": "An export is already running. Please wait."})
                job_id = uuid.uuid4().hex
                JOBS[job_id] = {"id": job_id, "status": "queued", "completed": 0, "total": len(ids)}
                threading.Thread(target=render, args=(job_id, ids), daemon=True).start()
                return self.reply(202, JOBS[job_id])
            return self.reply(404, {"error": "Not found"})
        except (json.JSONDecodeError, ValueError):
            self.reply(400, {"error": "Invalid request"})
        except Exception as error:
            LOG.warning("request failed: %s", type(error).__name__)
            self.reply(502, {"error": "VSS request failed. Please try again."})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler)
    LOG.info("ClipScout producer desk ready")
    server.serve_forever()
