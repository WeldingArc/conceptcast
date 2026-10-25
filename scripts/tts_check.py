#!/usr/bin/env python3
"""Check every recorded clip before it goes into the app.

    python3 scripts/tts_check.py COURSE_DIR [--raw]

Per clip (voice/clips by default, voice/raw with --raw):
- speaking rate vs. the course median (letters per second): catches truncated or runaway clips
- loudness: peak below -14 dB or mean below -38 dB means near-silent audio
- silence: internal gaps over 1.2 s, or more than 1 s of silence at the start
Very short lines (one or two words) often read "slow" because engines pad them to a minimum
length; English words inside other languages often read "fast". Both are usually fine; listen if unsure.
"""

import argparse
import json
import pathlib
import re
import statistics
import subprocess
from concurrent.futures import ThreadPoolExecutor


def probe(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(f), "-af", "silencedetect=noise=-45dB:d=1.0,volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    e = r.stderr
    mx = re.search(r"max_volume: (-?[\d.]+) dB", e)
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", e)
    sil = [(float(a), float(b)) for a, b in re.findall(r"silence_end: (-?[\d.]+) \| silence_duration: ([\d.]+)", e)]
    return {"max": float(mx.group(1)) if mx else None, "mean": float(mean.group(1)) if mean else None, "sil": sil}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course_dir")
    ap.add_argument("--raw", action="store_true")
    a = ap.parse_args()
    cdir = pathlib.Path(a.course_dir).resolve()
    lines = json.loads((cdir / "build" / "voice_lines.json").read_text(encoding="utf-8"))["lines"]
    d = cdir / "voice" / ("raw" if a.raw else "clips")
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    ids = [i for i in lines if i in man and (d / f"{i}.mp3").exists()]
    with ThreadPoolExecutor(8) as ex:
        res = dict(zip(ids, ex.map(lambda i: probe(d / f"{i}.mp3"), ids)))
    rate = {}
    for i in ids:
        n = len(re.sub(r"[\W_]", "", lines[i]))
        rate[i] = n / man[i]["dur"] if man[i]["dur"] else 0
    med = statistics.median(rate.values()) if rate else 0
    flags = []
    for i in ids:
        v, dur, why = res[i], man[i]["dur"], []
        if dur < 0.5:
            why.append(f"very short {dur}s")
        if med and not (med * 0.55 <= rate[i] <= med * 1.6):
            why.append(f"rate {rate[i]:.1f}/s vs median {med:.1f}")
        if v["max"] is None or v["max"] < -14:
            why.append(f"quiet: peak {v['max']} dB")
        if v["mean"] is not None and v["mean"] < -38:
            why.append(f"quiet: mean {v['mean']} dB")
        for end_t, sd in v["sil"]:
            start_t = end_t - sd
            if start_t > 0.3 and end_t < dur - 0.3 and sd > 1.2:
                why.append(f"gap {sd:.1f}s at {start_t:.1f}s")
            if start_t <= 0.05 and sd > 1.0:
                why.append(f"leading silence {sd:.1f}s")
        if why:
            flags.append((i, dur, why, lines[i]))
    missing = [i for i in lines if i not in ids]
    print(f"checked {len(ids)}/{len(lines)} · missing {len(missing)} · total {sum(man[i]['dur'] for i in ids) / 60:.1f} min · median {med:.2f} letters/s")
    if res:
        mx = [v["max"] for v in res.values() if v["max"] is not None]
        print(f"peak range {min(mx):.1f} … {max(mx):.1f} dB")
    print(f"flagged {len(flags)}")
    for i, dur, why, t in flags:
        print(f" - {i} ({dur}s) {', '.join(why)} | {t[:70]}")


if __name__ == "__main__":
    main()
