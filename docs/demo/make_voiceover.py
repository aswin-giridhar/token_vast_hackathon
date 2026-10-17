"""Generate a per-beat voiceover and mux it onto the existing 79s walkthrough.

The visuals are fixed, so each line is generated separately and padded with
silence to its own slide window. That keeps audio locked to the slide it
describes instead of drifting, which is what a single continuous take does.
"""
import json
import pathlib
import re
import subprocess
import sys
import urllib.request

FF = r"C:/Users/Aswin/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe"
FP = r"C:/Users/Aswin/AppData/Local/Microsoft/WinGet/Links/ffprobe.exe"
ENV = pathlib.Path(r"E:/Hackathon/all_things_agentic_hackathon/app/.env")
HERE = pathlib.Path(__file__).parent
VOICE = "JBFqnCBsd6RMkjVDRZzb"          # George — suits technical narration
RATE = 2.40                              # re-measured on this script: 183 words / 76.3s

# (window_seconds, line). Windows match the slide boundaries sampled from the
# source video: eight slides, ten seconds each, last one nine.
BEATS = [
    (10, "Finding a clip is only the start. Editors need the right shots, "
         "in a usable order, with sources they can defend."),
    (10, "ClipScout turns a brief into shot requests. Each one searches the real "
         "archive, using VAST storage with NVIDIA Cosmos descriptions and embeddings."),
    (10, "A Weights and Biases model proposes which clips fit, and in what order. "
         "The unsupported marathon finish is flagged, not forced."),
    (10, "Every suggestion is only a proposal. The editor opens the source and checks "
         "camera and timecodes. Approval stays locked until they confirm it fits."),
    (10, "Approved shots become the sequence. Reorder or remove them. Any missing scene "
         "stays visible on the coverage board instead of quietly disappearing."),
    (10, "Export gives a silent MP4 and a shot list with source IDs, "
         "original in and out points, and cut positions."),
    (10, "This is the real export. Fifteen seconds, assembled by FFmpeg from clips the "
         "editor approved — an archive montage, and the app says so."),
    (9,  "A reviewed cut, with evidence. VAST and NVIDIA retrieve. "
         "Weights and Biases proposes. The editor decides."),
]


def api_key() -> str:
    for line in ENV.read_text(errors="replace").splitlines():
        if line.strip().startswith("ELEVENLABS_API_KEY") and "=" in line:
            return line.split("=", 1)[1].strip().strip("\"'")
    sys.exit("No ELEVENLABS_API_KEY found")


def duration(path) -> float:
    out = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def run(args):
    result = subprocess.run(args, capture_output=True)
    if result.returncode:
        sys.exit(result.stderr.decode(errors="replace")[-1500:])


def speak(key, text, path):
    body = json.dumps({
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "speed": 1.0},
    }).encode()
    request = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}",
        data=body,
        headers={"xi-api-key": key, "Content-Type": "application/json",
                 "Accept": "audio/mpeg"})
    with urllib.request.urlopen(request, timeout=90) as response:
        path.write_bytes(response.read())


def main():
    key = api_key()
    work = HERE / "segments"
    work.mkdir(exist_ok=True)

    total_words = sum(len(re.findall(r"\S+", line)) for _, line in BEATS)
    total_window = sum(window for window, _ in BEATS)
    print(f"{total_words} words / {total_window}s window "
          f"= {total_words / RATE:.1f}s of speech predicted")

    padded = []
    for index, (window, line) in enumerate(BEATS, 1):
        raw = work / f"raw-{index:02d}.mp3"
        if not raw.exists():
            speak(key, line, raw)
        spoken = duration(raw)
        if spoken > window:
            print(f"  !! beat {index} overruns: {spoken:.2f}s > {window}s window")
        target = work / f"beat-{index:02d}.wav"
        # Pad (or hard-cut) each beat to exactly its slide window.
        run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw),
             "-af", f"apad=whole_dur={window}", "-t", str(window),
             "-ar", "48000", "-ac", "2", str(target)])
        got = duration(target)
        print(f"  beat {index}: spoken {spoken:5.2f}s -> padded {got:5.2f}s "
              f"(window {window}s)")
        padded.append(target)

    listing = work / "beats.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in padded), encoding="utf-8")
    voice = HERE / "voiceover.wav"
    run([FF, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c", "copy", str(voice)])
    print(f"voiceover.wav = {duration(voice):.2f}s")

    source = HERE / "original.mp4"
    output = HERE / "ClipScout_Walkthrough_Narrated.mp4"
    run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
         "-i", str(voice), "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
         "-movflags", "+faststart", str(output)])
    print(f"OUTPUT {output.name} = {duration(output):.2f}s "
          f"({output.stat().st_size / 1048576:.1f} MB)")


if __name__ == "__main__":
    main()
