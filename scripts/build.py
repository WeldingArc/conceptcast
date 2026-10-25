#!/usr/bin/env python3
"""Build a ConceptCast lesson app from a course file.

    python3 scripts/build.py path/to/course.json [--out DIR] [--no-audio]

The course file is JSON (or a .py file that defines COURSE = {...}); see references/course-schema.md.
Outputs (in --out, default: the course file's folder):
  <id>.html               the app: one self-contained file, double-click to open
  <id>.body.html          the same page without <html>/<head> wrappers (for hosts that add their own)
  build/narration.txt     every spoken line, beat by beat, for review
  build/voice_lines.json  {clip_id: text} for scripts/tts_render.py
Recorded clips found in voice/clips/<id>.mp3 are embedded; lines without a clip fall back
to the browser's built-in voice at runtime.
"""

import argparse
import base64
import hashlib
import html
import json
import pathlib
import random
import re
import runpy
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from langpacks import COMMON_SYMBOLS, NON_LATIN, pack  # noqa: E402

TEMPLATE = HERE.parent / "assets" / "player.html"
VIS_TYPES = {"tiles", "groups", "steps", "vs", "flow", "rows", "bars", "big", "triangle", "balance",
             "timeline", "quote", "table", "warn", "def"}
DEFAULT_COLORS = ["#2F7A80", "#B05A3C", "#5B5FA8", "#4E7F52", "#8A5A2B", "#7A4E7F", "#3D6E8F", "#8F3D52"]


# ---------------------------------------------------------------- text helpers
def t(s):
    """Plain text → safe HTML; **bold** becomes a highlighter mark on screen."""
    s = html.escape(str(s))
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return s.replace("\n", "<br>")


def end(s):
    s = s.strip()
    return s if not s or s[-1] in ".?!。" else s + "."


def batchim(word):
    """Korean: does the last syllable end in a final consonant (batchim)? Picks the particle form."""
    w = re.sub(r"[^\uAC00-\uD7A3A-Za-z0-9]", "", word)
    if not w:
        return False
    ch = w[-1]
    if "\uAC00" <= ch <= "\uD7A3":
        return (ord(ch) - 0xAC00) % 28 != 0
    return ch.isdigit() and ch in "013678"


def josa(word, pair):
    """pair = [form after a final consonant, form after a vowel]"""
    return word + (pair[0] if batchim(word) else pair[1])


class Speaker:
    """Turns on-screen text into words a TTS voice reads well, for one language."""

    def __init__(self, lang, names):
        self.lang = lang.split("-")[0]
        _, self.ph, self.sym = pack(lang)
        self.names = sorted((names or {}).items(), key=lambda kv: -len(kv[0]))

    def __call__(self, s):
        s = html.unescape(re.sub(r"<[^>]+>", "", str(s))).replace("**", "")
        ph = self.ph
        s = re.sub(r"(\d+)V(?![A-Za-z])", lambda m: ph["volts"].format(n=m.group(1)), s)
        s = re.sub(r"(\d)\s*~\s*(\d)", lambda m: ph["range"].format(a=m.group(1), b=m.group(2)), s)
        s = re.sub(r"\bp\.\s*(\d+)", lambda m: ph["page"].format(n=m.group(1)), s)
        # keep apostrophes inside words (I'm, can't); other quotes are dropped below
        s = re.sub(r"(?<=[A-Za-z])['’](?=[A-Za-z])", "\u0001", s)

        def paren(m):
            inner = m.group(1)
            if re.search(r"\d{4}", inner):                        # citations: (Author, 1999)
                return ""
            if self.lang in NON_LATIN and re.fullmatch(r"[A-Za-z0-9 .,&'’\"“”\-:;+−·!?\u0001]+", inner):
                return ""                                         # Latin gloss inside a non-Latin sentence
            return ", " + inner + ","
        for _ in range(2):
            if self.lang in NON_LATIN:
                s = re.sub(r"\s*\(([^()]*)\)(?=[\uAC00-\uD7A3\u3040-\u30FF\u4E00-\u9FFF])", "", s)  # (gloss) glued to a particle
            s = re.sub(r"\s*\(([^()]*)\)", paren, s)
        for en, native in self.names:
            s = re.sub(r"(?<![A-Za-z])" + re.escape(en) + r"(?![A-Za-z])", native, s)
        for a, b in self.sym + COMMON_SYMBOLS:
            s = s.replace(a, b)
        s = s.replace("\"", "").replace("“", "").replace("”", "").replace("'", "").replace("‘", "").replace("’", "")
        s = s.replace("\u0001", "'")
        if self.lang == "ko":
            s = re.sub(r"(?<=[\uAC00-\uD7A3])-(?=[\uAC00-\uD7A3])", " ", s)
        s = re.sub(r"\s*,\s*,+", ",", s)
        s = re.sub(r",\s*([.?!])", r"\1", s)
        return re.sub(r"\s+", " ", s).strip(" ,")

    def name_only(self, s):
        return self(re.sub(r"\s*\([^)]*\)", "", s))


# ---------------------------------------------------------------- beats + narration
def vis_beats(v, say, lang):
    """One diagram → [(item index, spoken line)]; index -1 = the diagram's title/intro."""
    ph = say.ph
    ko = say.lang == "ko"
    tp = v["type"]
    out = []
    if tp in ("tiles", "steps", "rows", "bars") and v.get("title"):
        out.append((-1, end(say(v["title"]))))
    if tp == "tiles":
        out += [(k, end(say(x))) for k, x in enumerate(v["items"])]
    elif tp == "groups":
        for k, g in enumerate(v["groups"]):
            parts = [say(g["name"])]
            tag = say(g.get("tag", ""))
            if len(tag) > 1:
                parts.append(tag)
            if g["items"]:
                parts.append(", ".join(say(x) for x in g["items"]))
            out.append((k, ". ".join(end(p)[:-1] for p in parts if p) + "."))
    elif tp == "steps":
        for k, (name, desc) in enumerate(v["items"]):
            o = ph["ordinals"][k] if k < len(ph["ordinals"]) else str(k + 1)
            out.append((k, ph.get("step", "{o}, {name}").format(o=o, name=end(say(name))) + (f" {end(say(desc))}" if desc else "")))
    elif tp == "vs":
        L, R = say.name_only(v["left"]), say.name_only(v["right"])
        out.append((-1, ph["vsIntro"].format(L=L, R=R)))
        for k, (lab, a, b) in enumerate(v["rows"]):
            seg = [end(say(lab))] if lab else []
            for side, text in ((L, a), (R, b)):
                if text:
                    seg.append(end(f"{josa(side, ph['topicParticle'])} {say(text)}") if ko else ph["vsSide"].format(side=side, text=say(text)))
            out.append((k, " ".join(seg)))
        if v.get("win"):
            w = L if v["win"] == "left" else R
            wt = say(v.get("winText", ""))
            out.append((len(v["rows"]), end(f"{josa(w, ph['subjectParticle'])} {wt}") if ko else ph["win"].format(W=w, winText=wt)))
    elif tp == "flow":
        out += [(k, end(say(n))) for k, n in enumerate(v["nodes"])]
        for j, br in enumerate(v.get("branch", [])):
            out.append((len(v["nodes"]) + j, end(say(br[0])) + " " + end(say(br[1]))))
    elif tp == "rows":
        for k, (lab, chain) in enumerate(v["rows"]):
            out.append((k, end(say(lab)) + " " + end(", ".join(say(c) for c in chain))))
    elif tp == "bars":
        for k, (lab, val) in enumerate(v["items"]):
            unit = ph["percent"] if v.get("unit") == "%" else (" " + v["unit"] if v.get("unit") and not ko else v.get("unit", ""))
            out.append((k, f"{say(lab)}, {'%g' % val}{unit}."))
        if "star" in v:
            out.append((len(v["items"]), end(say(v["items"][v["star"]][0]) + ", " + say(v["starText"]))))
    elif tp == "big":
        out += [(k, end(say(a)) + " " + end(say(b))) for k, (a, b) in enumerate(v["items"])]
    elif tp == "triangle":
        p, o, x = say(v["p"]), say(v["o"]), say(v["x"])
        out += [(i, ph["tri"][i].format(p=p, o=o, x=x)) for i in range(3)] + [(3, end(say(v["caption"])))]
    elif tp == "balance":
        out += [(0, end(say(v["left"]))), (1, end(say(v["right"]))), (2, end(say(v["caption"])))]
    elif tp == "timeline":
        out += [(k, end(say(a)) + " " + end(say(b))) for k, (a, b) in enumerate(v["items"])]
    elif tp == "quote":
        out.append((0, end(say(v["by"])) + " " + end(say(v["text"]))))
    elif tp == "table":
        h = v["head"]
        for k, r in enumerate(v["rows"]):
            if len(r) == 2:
                out.append((k, end(say(r[0])) + " " + end(say(r[1]))))
            else:
                out.append((k, end(say(r[0])) + " " + " ".join(end(say(h[c]) + ", " + say(r[c])) for c in range(1, len(r)))))
    elif tp == "warn":
        out.append((0, end(say(v["text"]))))
    elif tp == "def":
        out.append((0, ph["def"].format(term=say(v["term"])) + end(say(v["text"]))))
    fix = v.get("say", {})
    keys = {i for i, _ in out}
    for k in fix:
        if int(k) not in keys:
            raise ValueError(f"'say' key {k} has no matching step in a {tp} diagram (steps: {sorted(keys)})")
    return [(i, fix.get(str(i), fix.get(i, s))) for i, s in out]


def card_beats(c, say):
    ph = say.ph
    beats = [{"t": "title", "say": c.get("sayTitle") or end(say(c["title"]))},
             {"t": "one", "say": c.get("sayOne") or end(say(c["one"]))}]
    for vi, v in enumerate(c.get("vis", [])):
        if v["type"] not in VIS_TYPES:
            raise ValueError(f"card {c['id']}: unknown diagram type '{v['type']}' (allowed: {sorted(VIS_TYPES)})")
        for i, s in vis_beats(v, say, say.lang):
            beats.append({"t": "vis", "v": vi, "i": i, "say": s})
    if c.get("hook"):
        beats.append({"t": "hook", "say": ph["hook"] + (c.get("sayHook") or end(say(c["hook"])))})
    if c.get("terms"):
        beats.append({"t": "terms", "say": c.get("sayTerms") or (ph["terms"] + end(", ".join(say(x) for x in c["terms"])))})
    if c.get("ex"):
        beats.append({"t": "ex", "say": c.get("sayEx") or (ph["ex"] + end(say(c["ex"])))})
    return beats


def html_vis(v):
    o = {k: v[k] for k in v if k != "say"}
    for key in ("title", "left", "right", "winText", "p", "o", "x", "caption", "text", "by", "starText", "top", "bottom", "term"):
        if key in o:
            o[key] = t(o[key])
    if "items" in o:
        o["items"] = [t(x) if isinstance(x, str) else [t(y) if isinstance(y, str) else y for y in x] for x in o["items"]]
    if "groups" in o:
        o["groups"] = [{"name": t(g["name"]), "tag": t(g.get("tag", "")), "items": [t(x) for x in g["items"]]} for g in o["groups"]]
    if "rows" in o:
        o["rows"] = ([[t(lab), [t(x) for x in chain]] for lab, chain in o["rows"]] if o["type"] == "rows"
                     else [[t(x) for x in r] for r in o["rows"]])
    for key in ("head", "nodes"):
        if key in o:
            o[key] = [t(x) for x in o[key]]
    if "branch" in o:
        o["branch"] = [[t(b[0]), t(b[1]), b[2] if len(b) > 2 else ""] for b in o["branch"]]
    return o


def balance_options(bank, seed):
    """Shuffle multiple-choice options deterministically so the right answer is spread across positions."""
    rnd = random.Random(seed)
    mcs = [q for q in bank if q["type"] == "mc" and not q.get("fixedOrder")]
    targets = [i % 4 for i in range(len(mcs))]
    rnd.shuffle(targets)
    for q, tgt in zip(mcs, targets):
        n = len(q["opts"])
        tgt = tgt % n
        right = q["opts"][q["a"]]
        others = [o for i, o in enumerate(q["opts"]) if i != q["a"]]
        rnd.shuffle(others)
        q["opts"] = others[:tgt] + [right] + others[tgt:]
        q["a"] = tgt


def load_course(path):
    p = pathlib.Path(path)
    if p.suffix == ".py":
        return runpy.run_path(str(p))["COURSE"]
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- main
def build(course_path, out_dir=None, embed_audio=True):
    course = load_course(course_path)
    cdir = pathlib.Path(course_path).resolve().parent
    out = pathlib.Path(out_dir).resolve() if out_dir else cdir
    (out / "build").mkdir(parents=True, exist_ok=True)
    lang = course.get("lang", "en")
    ui, ph, _ = pack(lang)
    ui = dict(ui, **course.get("ui", {}))
    ph = dict(ph, **course.get("phrases", {}))
    say = Speaker(lang, course.get("names", {}))
    say.ph = ph
    voice = dict({"engine": "browser"}, **course.get("voice", {}))
    vkey = f"{voice['engine']}:{voice.get('voice', '')}"

    bank = [dict(q) for q in course.get("bank", [])]
    if course.get("shuffleOptions", True):
        balance_options(bank, course.get("id", "course"))
    bank_by = {q["id"]: q for q in bank}
    problems, script, used = [], [], {}
    risky = re.compile(r"[<>=✗○→↔↑↓÷×~\"+−()\[\]]" + (r"|[A-Za-z]{2,}" if say.lang in NON_LATIN else ""))
    allow = re.compile("|".join(map(re.escape, course.get("allowInNarration", []))) or r"(?!)")

    chapters = []
    for ci, ch in enumerate(course["chapters"]):
        n = len(ch["cards"])
        intro = ch.get("sayIntro") or ph["intro"].format(name=ch["name"], sub=end(say(ch.get("sub", ""))) if ch.get("sub") else "", n=n).replace("  ", " ")
        outro = ch.get("sayOutro") or ph["outro"].format(name=ch["name"])
        script.append(f"\n######## {ch['name']}\n[intro] {intro}")
        cards = []
        for c in ch["cards"]:
            beats = card_beats(c, say)
            for qid in c.get("qids", []):
                if qid not in bank_by:
                    problems.append(f"{c['id']}: question {qid} is not in the bank")
                used.setdefault(qid, []).append(c["id"])
            script.append(f"\n== {c['id']} {c['title']}")
            for k, b in enumerate(beats):
                tag = b["t"] + (f" v{b['v']}.{b['i']}" if b["t"] == "vis" else "")
                script.append(f"  {k:>2} [{tag}] {b['say']}")
                if risky.search(allow.sub("", b["say"])):
                    problems.append(f"{c['id']} #{k} [{tag}] check how this reads aloud: {b['say']}")
            cards.append({"id": c["id"], "title": t(c["title"]), "terms": [t(x) for x in c.get("terms", [])],
                          "one": t(c["one"]), "vis": [html_vis(v) for v in c.get("vis", [])], "hook": t(c.get("hook", "")),
                          "ex": t(c.get("ex", "")), "qids": c.get("qids", []), "beats": beats})
        script.append(f"[outro] {outro}")
        chapters.append({"id": ch.get("id", f"ch{ci + 1}"), "name": ch["name"], "sub": t(ch.get("sub", "")),
                         "chips": ch.get("chips", []), "color": ch.get("color", DEFAULT_COLORS[ci % len(DEFAULT_COLORS)]),
                         "intro": intro, "outro": outro, "cards": cards})
    for q in bank:
        if q["id"] not in used:
            problems.append(f"question {q['id']} is not attached to any card (it will never be asked)")
    for qid, cards_ in used.items():
        if len(cards_) > 1:
            problems.append(f"question {qid} is attached to several cards: {cards_}")

    # ---- spoken lines → clip ids
    lines = {}

    def reg(text):
        i = hashlib.sha1((vkey + "|" + text).encode("utf-8")).hexdigest()[:12]
        lines[i] = text
        return i
    for ch in chapters:
        ch["auIntro"], ch["auOutro"] = reg(ch["intro"]), reg(ch["outro"])
        for c in ch["cards"]:
            for b in c["beats"]:
                b["au"] = reg(b["say"])
    fixed_keys = ["listEnd", "ok", "oxO", "oxX", "resWrong", "resPerfect", "sample"]
    fixed = {k: {"say": ph[k], "au": reg(ph[k])} for k in fixed_keys}
    qbank = {}
    for qid in used:
        if qid not in bank_by:
            continue
        q = {k: (t(v) if k in ("q", "exp", "ref") else v) for k, v in bank_by[qid].items()}
        if q["type"] == "mc":
            q["opts"] = [t(o) for o in bank_by[qid]["opts"]]
        sq = bank_by[qid].get("sayQ") or end(say(bank_by[qid]["q"]))
        if q["type"] == "ox":
            sq += ph["oxSuffix"]
            q["auNo"] = fixed["oxO" if q["a"] == "O" else "oxX"]["au"]
        else:
            sa = bank_by[qid].get("sayA") or end(say(bank_by[qid]["opts"][bank_by[qid]["a"]]))
            q["sayA"] = sa
            q["auNo"] = reg(ph["wrongPrefix"] + sa)
        q["sayQ"], q["auQ"] = sq, reg(sq)
        for txt in [sq] + ([q["sayA"]] if q["type"] == "mc" else []):
            if risky.search(allow.sub("", txt)):
                problems.append(f"{qid} quiz narration — check how this reads aloud: {txt}")
        qbank[qid] = q
    (out / "build" / "voice_lines.json").write_text(json.dumps({"voice": voice, "lines": lines}, ensure_ascii=False, indent=1), encoding="utf-8")

    audio, adur, missing = {}, {}, 0
    clip_dir = out / "voice" / "clips"
    man_path = clip_dir / "manifest.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {}
    if embed_audio and voice["engine"] != "browser":
        for i in lines:
            f = clip_dir / f"{i}.mp3"
            if f.exists() and manifest.get(i, {}).get("text") == lines[i]:
                audio[i] = base64.b64encode(f.read_bytes()).decode("ascii")
                adur[i] = manifest[i].get("dur", 0)
            else:
                missing += 1

    # ---- template
    tpl = TEMPLATE.read_text(encoding="utf-8")
    keys = set(re.findall(r'T\("([A-Za-z0-9]+)"', tpl))
    lacking = sorted(k for k in keys if k not in ui)
    if lacking:
        problems.append(f"UI strings missing for '{lang}': {lacking} (add them to course['ui'] or scripts/langpacks.py)")
    data = {
        "id": course.get("id", "course"), "title": course.get("title", ""), "subtitle": course.get("subtitle", ""),
        "lang": lang.split("-")[0], "locale": course.get("locale", {"ko": "ko-KR", "en": "en-US"}.get(lang.split("-")[0], lang)),
        "preferVoice": course.get("preferBrowserVoice", ""), "exam": course.get("exam"), "footer": t(course["footer"]) if course.get("footer") else "",
        "ui": ui, "chapters": chapters, "bank": qbank, "fixed": fixed,
        "voiceName": voice.get("label", ""), "audio": audio, "adur": adur,
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    body = tpl.replace("__TITLE__", html.escape(course.get("title", "ConceptCast"))).replace("__DATA_JSON__", payload)
    cid = course.get("id", "course")
    (out / f"{cid}.body.html").write_text(body, encoding="utf-8")
    full = (f"<!doctype html>\n<html lang=\"{lang}\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            f"</head>\n<body>\n{body}\n</body>\n</html>\n")
    (out / f"{cid}.html").write_text(full, encoding="utf-8")
    (out / "build" / "narration.txt").write_text("\n".join(script), encoding="utf-8")
    node = shutil.which("node")
    if node:  # catch template syntax errors before anyone opens the app
        js = out / "build" / "player_check.js"
        js.write_text(re.findall(r"<script>(.*?)</script>", body, re.S)[0], encoding="utf-8")
        r = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
        js.unlink()
        if r.returncode:
            problems.append("JavaScript syntax error in the player: " + r.stderr.strip()[:400])

    nb = sum(len(c["beats"]) for ch in chapters for c in ch["cards"])
    print(f"chapters {len(chapters)} · concepts {sum(len(ch['cards']) for ch in chapters)} · beats {nb} · questions {len(qbank)}")
    print(f"app: {out / (cid + '.html')} ({(out / (cid + '.html')).stat().st_size // 1024} KB)")
    print(f"spoken lines {len(lines)} · embedded clips {len(audio)} · without clip {len(lines) - len(audio)} "
          f"(voice: {voice['engine']}{' ' + voice.get('voice', '') if voice.get('voice') else ''})")
    if problems:
        print(f"\nto check ({len(problems)}):")
        for p in problems:
            print(" -", p)
    return {"problems": problems, "lines": len(lines), "audio": len(audio)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course")
    ap.add_argument("--out")
    ap.add_argument("--no-audio", action="store_true", help="do not embed recorded clips")
    a = ap.parse_args()
    build(a.course, a.out, not a.no_audio)
