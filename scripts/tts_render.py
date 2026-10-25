#!/usr/bin/env python3
"""Record every spoken line of a course with the voice chosen in course.json → "voice".

    python3 scripts/tts_render.py COURSE_DIR                 # record build/voice_lines.json (missing clips only)
    python3 scripts/tts_render.py COURSE_DIR --audition      # one sample per voice in voice.candidates, played aloud
    python3 scripts/tts_render.py COURSE_DIR --audition --no-play   # same, silent (for tests)
    python3 scripts/tts_render.py --list-voices edge ko      # list voices of an engine for a language

COURSE_DIR is the build output folder (the course file's folder unless you built with --out).
Run build.py first: it writes build/voice_lines.json. --audition reads the voice settings straight
from the course file in COURSE_DIR when there is one, so edits to voice.candidates apply without a rebuild.

Engines (course.json → "voice": {"engine": ..., "voice": ..., ...}):
  edge        Microsoft neural voices via edge-tts. Free, online, no key. Run through uv:
              uv run --with edge-tts python scripts/tts_render.py ...         (TESTED)
  say         macOS built-in voices (`say -v`). Offline; quality depends on the voice
              (download "Premium"/"Enhanced" voices in System Settings).    (TESTED)
  openai      OpenAI speech API. Needs OPENAI_API_KEY. "model" default gpt-4o-mini-tts.   (untested here)
  gemini      Gemini TTS. Needs GEMINI_API_KEY. "model" default gemini-2.5-flash-preview-tts.  (untested here)
  elevenlabs  ElevenLabs. Needs ELEVENLABS_API_KEY; "voice" is a voice_id.  (untested here)
  command     Any local/open-source TTS CLI (Piper, Kokoro, MeloTTS, Qwen3-TTS via mlx-audio, ...):
              "command": "piper --model ko.onnx --output_file {out}"  — text arrives on stdin,
              or put {text} in the command. {out} gets a .wav path.        (generic)
  browser     No recording: the app uses the browser's built-in voice at runtime.

Untested engines are written from the providers' public API docs; the audition step exists to
catch a wrong model name, key, or response format before a long render.
Every saved clip is logged to voice/raw/manifest.json as soon as it is written.
"""

import argparse
import asyncio
import base64
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

FFMPEG = shutil.which("ffmpeg")


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 3)
    except ValueError:
        return 0.0


def to_mp3(src, dst, raw_pcm=None):
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    cmd += (["-f", "s16le", "-ar", str(raw_pcm), "-ac", "1"] if raw_pcm else []) + ["-i", str(src), "-c:a", "libmp3lame", "-b:a", "64k", str(dst)]
    subprocess.run(cmd, check=True)


def http_json(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


# ---------------------------------------------------------------- engines (sync, run in threads)
def synth(engine, cfg, text, out_mp3):
    out_mp3 = pathlib.Path(out_mp3)
    if engine == "edge":
        import edge_tts  # uv run --with edge-tts
        kw = {k: cfg[k] for k in ("rate", "pitch", "volume") if k in cfg}
        asyncio.run(edge_tts.Communicate(text, cfg["voice"], **kw).save(str(out_mp3)))
    elif engine == "say":
        with tempfile.TemporaryDirectory() as d:
            aiff = pathlib.Path(d) / "a.aiff"
            subprocess.run(["say", "-v", cfg["voice"], "-o", str(aiff), text], check=True)
            to_mp3(aiff, out_mp3)
    elif engine == "openai":
        key = os.environ["OPENAI_API_KEY"]
        body = {"model": cfg.get("model", "gpt-4o-mini-tts"), "voice": cfg.get("voice", "alloy"), "input": text, "response_format": "mp3"}
        if cfg.get("instructions"):
            body["instructions"] = cfg["instructions"]
        out_mp3.write_bytes(http_json("https://api.openai.com/v1/audio/speech", body, {"Authorization": f"Bearer {key}"}))
    elif engine == "gemini":
        key = os.environ["GEMINI_API_KEY"]
        model = cfg.get("model", "gemini-2.5-flash-preview-tts")
        prompt = (cfg["style"] + ": " + text) if cfg.get("style") else text
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["AUDIO"],
                                     "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": cfg.get("voice", "Kore")}}}}}
        res = json.loads(http_json(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", body, {"x-goog-api-key": key}))
        pcm = base64.b64decode(res["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
        with tempfile.TemporaryDirectory() as d:
            raw = pathlib.Path(d) / "a.pcm"
            raw.write_bytes(pcm)
            to_mp3(raw, out_mp3, raw_pcm=cfg.get("sampleRate", 24000))
    elif engine == "elevenlabs":
        key = os.environ["ELEVENLABS_API_KEY"]
        body = {"text": text, "model_id": cfg.get("model", "eleven_multilingual_v2")}
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{cfg['voice']}?output_format=mp3_44100_128"
        out_mp3.write_bytes(http_json(url, body, {"xi-api-key": key}))
    elif engine == "command":
        with tempfile.TemporaryDirectory() as d:
            wav = pathlib.Path(d) / "a.wav"
            cmd = cfg["command"].replace("{out}", shlex.quote(str(wav)))
            uses_text = "{text}" in cmd
            cmd = cmd.replace("{text}", shlex.quote(text))
            subprocess.run(cmd, shell=True, check=True, input=None if uses_text else text.encode())
            to_mp3(wav, out_mp3)
    else:
        raise SystemExit(f"unknown engine '{engine}'")
    if not out_mp3.exists() or out_mp3.stat().st_size < 800:
        raise RuntimeError("no audio produced")


def list_voices(engine, lang):
    if engine == "edge":
        import edge_tts
        vs = asyncio.run(edge_tts.list_voices())
        for v in vs:
            if v["Locale"].lower().startswith(lang.lower()):
                print(f'{v["ShortName"]:40} {v["Gender"]:7} {", ".join(v.get("VoiceTag", {}).get("VoicePersonalities", []))}')
    elif engine == "say":
        out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            if f" {lang}_" in line or line.split("#")[0].strip().endswith(lang):
                print(line)
    else:
        print("See the provider's voice list (references/tts-options.md).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course_dir", nargs="?")
    ap.add_argument("--audition", action="store_true", help="one sample per voice in course.json → voice.candidates")
    ap.add_argument("--text", help="sample text for --audition (default: a typical narration line from the course)")
    ap.add_argument("--no-play", action="store_true")
    ap.add_argument("--list-voices", nargs=2, metavar=("ENGINE", "LANG"))
    ap.add_argument("--workers", type=int)
    a = ap.parse_args()
    if a.list_voices:
        list_voices(*a.list_voices)
        return
    cdir = pathlib.Path(a.course_dir).resolve()
    if not FFMPEG:
        sys.exit("ffmpeg is required (brew install ffmpeg)")
    vl = cdir / "build" / "voice_lines.json"
    if not vl.exists():
        sys.exit(f"{vl} not found. Run `python3 scripts/build.py <course file>` first (COURSE_DIR is the build output folder).")
    spec = json.loads(vl.read_text(encoding="utf-8"))
    cfg, lines = spec["voice"], spec["lines"]
    if a.audition:  # use the latest voice settings from the course file, so candidate edits need no rebuild
        for name in ("course.json", "course.py"):
            cf = cdir / name
            if cf.exists():
                import runpy
                course = json.loads(cf.read_text(encoding="utf-8")) if name.endswith(".json") else runpy.run_path(str(cf))["COURSE"]
                cfg = dict({"engine": "browser"}, **course.get("voice", {}))
                break
    engine = cfg["engine"]
    if engine == "browser":
        print("voice.engine is 'browser': nothing to record.")
        return

    if a.audition:
        engine = cfg["engine"]
        cands = cfg.get("candidates") or [{"engine": engine, "voice": cfg.get("voice")}]
        vals = list(lines.values())
        text = a.text or next((x for x in vals[2:] if 40 <= len(x) <= 160), vals[0])
        out = cdir / "voice" / "audition"
        out.mkdir(parents=True, exist_ok=True)
        for i, c in enumerate(cands, 1):
            c = dict(cfg, **c)
            f = out / f"{i}-{c['engine']}-{str(c.get('voice', 'cmd')).replace('/', '_')}.mp3"
            try:
                synth(c["engine"], c, text, f)
                print(f"{i}. {c['engine']} {c.get('voice', '')}: {f} ({duration(f)}s)")
                if not a.no_play and shutil.which("afplay"):
                    subprocess.run(["afplay", str(f)])
                    time.sleep(0.6)
            except Exception as e:  # noqa: BLE001
                print(f"{i}. {c['engine']} {c.get('voice', '')}: FAILED {type(e).__name__}: {str(e)[:200]}")
        return

    raw = cdir / "voice" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    mpath = raw / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    todo = [(i, t) for i, t in lines.items() if not ((raw / f"{i}.mp3").exists() and manifest.get(i, {}).get("text") == t)]
    workers = a.workers or {"edge": 5, "openai": 3, "gemini": 2, "elevenlabs": 2}.get(engine, 2)
    print(f"engine {engine} · voice {cfg.get('voice', cfg.get('command', ''))} · lines {len(lines)} · to record {len(todo)} · workers {workers}", flush=True)
    from concurrent.futures import ThreadPoolExecutor
    import threading
    lock = threading.Lock()
    st = {"ok": 0, "fail": 0, "streak": 0, "stop": False}
    t0 = time.time()

    def one(item):
        i, text = item
        if st["stop"]:
            return
        dst, part = raw / f"{i}.mp3", raw / f"{i}.part.mp3"
        err = ""
        for attempt in range(3):
            try:
                synth(engine, cfg, text, part)
                part.rename(dst)
                with lock:
                    manifest[i] = {"text": text, "engine": engine, "voice": cfg.get("voice", ""), "dur": duration(dst)}
                    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=0), encoding="utf-8")
                    st["ok"] += 1
                    st["streak"] = 0
                    if st["ok"] % 50 == 0:
                        print(f"  {st['ok']}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)
                return
            except Exception as e:  # noqa: BLE001
                err = f"{type(e).__name__}: {e}"[:200]
                time.sleep(2 + attempt * 4)
        with lock:
            st["fail"] += 1
            st["streak"] += 1
            print(f"  FAILED {i}: {err} | {text[:50]}", flush=True)
            if st["streak"] >= 8:
                st["stop"] = True
                print("Too many failures in a row; stopping. Fix the cause (key, model name, network) before retrying.", flush=True)
        if part.exists():
            part.unlink()

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, todo))
    total = sum(m["dur"] for k, m in manifest.items() if k in lines)
    print(f"done: recorded {st['ok']}, failed {st['fail']}, {time.time() - t0:.0f}s · total audio {total / 60:.1f} min", flush=True)
    sys.exit(1 if st["fail"] else 0)


if __name__ == "__main__":
    main()
