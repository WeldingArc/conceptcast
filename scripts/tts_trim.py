#!/usr/bin/env python3
"""Trim silence and re-encode recorded clips, then prove no speech was cut.

    python3 scripts/tts_trim.py COURSE_DIR [--bitrate 40k]

voice/raw/<id>.mp3 → voice/clips/<id>.mp3 (+ voice/clips/manifest.json)
- keeps 0.04 s before the first sound and 0.12 s after the last (TTS engines pad ~0.2 s / ~0.6 s)
- mono, 24 kHz, MP3 (plays everywhere; about 0.3 MB per spoken minute at 40 kbps)
- compares the length of the spoken part (above -45 dB) before and after: must match within 0.15 s
"""

import argparse
import json
import pathlib
import subprocess
from concurrent.futures import ThreadPoolExecutor

AF = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.04,areverse,"
      "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse")


def dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return round(float(r.stdout.strip() or 0), 3)


def speech_len(p):
    """Length between the first and last non-silent sample."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p), "-af", "silencedetect=noise=-45dB:d=0.1", "-f", "null", "-"],
                       capture_output=True, text=True)
    total = dur(p)
    starts = [float(x.split("silence_start: ")[1].split()[0]) for x in r.stderr.splitlines() if "silence_start" in x]
    ends = [float(x.split("silence_end: ")[1].split()[0]) for x in r.stderr.splitlines() if "silence_end" in x]
    lead = ends[0] if starts and starts[0] <= 0.01 and ends else 0.0
    tail = total - starts[-1] if starts and (len(ends) < len(starts) or ends[-1] >= total - 0.01) else 0.0
    return max(0.0, total - lead - tail)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course_dir")
    ap.add_argument("--bitrate", default="40k")
    a = ap.parse_args()
    cdir = pathlib.Path(a.course_dir).resolve()
    if not (cdir / "build" / "voice_lines.json").exists():
        raise SystemExit(f"{cdir / 'build' / 'voice_lines.json'} not found. Run build.py first (COURSE_DIR is the build output folder).")
    lines = json.loads((cdir / "build" / "voice_lines.json").read_text(encoding="utf-8"))["lines"]
    raw, clips = cdir / "voice" / "raw", cdir / "voice" / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    if not (raw / "manifest.json").exists():
        raise SystemExit(f"No recordings in {raw}. Run tts_render.py {cdir} first.")
    raw_man = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    old = json.loads((clips / "manifest.json").read_text(encoding="utf-8")) if (clips / "manifest.json").exists() else {}

    def one(i):
        src, dst = raw / f"{i}.mp3", clips / f"{i}.mp3"
        if not dst.exists() or old.get(i, {}).get("text") != lines[i]:
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-af", AF,
                            "-ac", "1", "-ar", "24000", "-c:a", "libmp3lame", "-b:a", a.bitrate, str(dst)], check=True)
        s0, s1 = speech_len(src), speech_len(dst)
        return i, {"text": lines[i], "dur": dur(dst), "orig": raw_man[i]["dur"], "speech0": round(s0, 3), "speech1": round(s1, 3),
                   "bytes": dst.stat().st_size}

    todo = [i for i in lines if i in raw_man and (raw / f"{i}.mp3").exists()]
    with ThreadPoolExecutor(8) as ex:
        man = dict(ex.map(one, todo))
    (clips / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=0), encoding="utf-8")
    bad = [(i, m) for i, m in man.items() if abs(m["speech1"] - m["speech0"]) > 0.15 or m["dur"] > m["orig"] + 0.05 or m["dur"] < 0.3]
    missing = [i for i in lines if i not in man]
    print(f"trimmed {len(man)}/{len(lines)} · {sum(m['orig'] for m in man.values()) / 60:.1f} → {sum(m['dur'] for m in man.values()) / 60:.1f} min · "
          f"{sum(m['bytes'] for m in man.values()) / 1e6:.1f} MB · speech changed >0.15 s: {len(bad)} · not recorded yet: {len(missing)}")
    for i, m in bad[:30]:
        print(f" - {i}: speech {m['speech0']} → {m['speech1']} s | {m['text'][:60]}")


if __name__ == "__main__":
    main()
