#!/usr/bin/env python3
"""Build a ConceptCast lesson app from a course file.

    python3 scripts/build.py path/to/course.json [--out DIR] [--no-audio]
    python3 scripts/build.py --print-strings [LANG]     # every translatable string, as JSON

The course file is JSON (or a .py file that defines COURSE = {...}); see references/course-schema.md.
Outputs (in --out, default: the course file's folder; this folder is also the COURSE_DIR that
the tts_*.py scripts take):
  <id>.html               the app: one self-contained file, double-click to open
  <id>.body.html          the same page without <html>/<head> wrappers (for hosts that add their own)
  build/narration.txt     every spoken line (beats, then fixed lines, then quiz lines), for review
  build/review.txt        each card with its attached questions and correct answers (Gate A input)
  build/voice_lines.json  {clip_id: text} for scripts/tts_render.py
Recorded clips found in OUT/voice/clips/<id>.mp3 are embedded; lines without a clip fall back
to the browser's built-in voice at runtime.
Exit code 1 means the course has an error that would break the app; fix it and rebuild.
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
from langpacks import COMMON_SYMBOLS, NON_LATIN, PHRASES, UI, pack  # noqa: E402

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

    def __init__(self, lang, names, phrases, symbols):
        self.lang = lang.split("-")[0]
        self.ph, self.sym = phrases, symbols
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
            parts = [x.strip() for x in inner.split(";")]
            # a bare year, or "Name, 1999" / "Name et al. 1999" / "Name 등, 1999" (comma or et al. before the year)
            cite = r"(?:[^\d]*[A-Z\uAC00-\uD7A3][^\d]*(?:,|\bet al\.?|등)\s*)?(1[6-9]|20)\d\d[a-z]?"
            if all(re.fullmatch(cite, x) for x in parts):   # citations: (2003), (Author, 1999; X, 2001b)
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
        u = str(v.get("unit", "")).strip()
        unit = ph["percent"] if u == "%" else (" " + say(u) if re.match(r"[A-Za-z]", u) else say(u))
        for k, (lab, val) in enumerate(v["items"]):
            out.append((k, f"{say(lab)}, {'%g' % val}{unit}."))
        if v.get("star") is not None:
            out.append((len(v["items"]), end(say(v["items"][v["star"]][0]) + (", " + say(v["starText"]) if v.get("starText") else ""))))
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
    fix = {int(k): txt for k, txt in v.get("say", {}).items()}   # keys were validated as integers
    keys = {i for i, _ in out}
    for k in fix:
        if k not in keys:
            raise CourseError(f"a {tp} diagram has a 'say' override for step {k}, but its steps are {sorted(keys)} "
                              f"(-1 = the diagram's intro/title; see references/visual-types.md)")
    return [(i, fix.get(i, s)) for i, s in out]


def card_beats(c, say):
    ph = say.ph
    beats = [{"t": "title", "say": c.get("sayTitle") or end(say(c["title"]))},
             {"t": "one", "say": c.get("sayOne") or end(say(c["one"]))}]
    for vi, v in enumerate(c.get("vis", [])):
        try:
            vb = vis_beats(v, say, say.lang)
        except CourseError as e:
            raise CourseError(f"card {c['id']}, diagram {vi + 1}: {e}") from None
        for i, s in vb:
            beats.append({"t": "vis", "v": vi, "i": i, "say": s})
    if c.get("hook"):
        beats.append({"t": "hook", "say": ph["hook"] + (c.get("sayHook") or end(say(c["hook"])))})
    if c.get("terms"):
        beats.append({"t": "terms", "say": ph["terms"] + (c.get("sayTerms") or end(", ".join(say(x) for x in c["terms"])))})
    if c.get("ex"):
        beats.append({"t": "ex", "say": ph["ex"] + (c.get("sayEx") or end(say(c["ex"])))})
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
    if o["type"] == "bars":
        o.setdefault("unit", "")
        o.setdefault("starText", "")
        if not o.get("max"):
            o["max"] = max([x[1] for x in v["items"]] + [1])
    return o


# ---------------------------------------------------------------- validation
class CourseError(Exception):
    """A course mistake that would break the app."""


REQUIRED = {  # diagram type → required fields
    "tiles": ["items"], "groups": ["groups"], "steps": ["items"], "vs": ["left", "right", "rows"],
    "flow": ["nodes"], "rows": ["rows"], "bars": ["items"], "big": ["items"], "triangle": ["p", "o", "x", "caption"],
    "balance": ["left", "right", "top", "bottom", "caption"], "timeline": ["items"], "quote": ["text", "by"],
    "table": ["head", "rows"], "warn": ["text"], "def": ["term", "text"],
}
OX_TRUE, OX_FALSE = {"o", "true", "t", "yes", "1"}, {"x", "false", "f", "no", "0"}


def validate(course):
    """Return a list of errors that would break the app (empty = fine). Normalizes true/false answers in place."""
    errs = []
    if not isinstance(course.get("chapters"), list) or not course["chapters"]:
        return ["the course has no 'chapters' list"]
    bank_ids = {}
    for qi, q in enumerate(course.get("bank", [])):
        where = f"bank[{qi}] ({q.get('id', 'no id')})"
        if "id" not in q:
            errs.append(f"{where}: missing 'id'")
            continue
        if q["id"] in bank_ids:
            errs.append(f"question id '{q['id']}' is used twice in the bank")
        bank_ids[q["id"]] = q
        if not q.get("q"):
            errs.append(f"{where}: missing question text 'q'")
        if q.get("type") == "mc":
            opts = q.get("opts")
            if not isinstance(opts, list) or len(opts) < 2:
                errs.append(f"{where}: a multiple-choice question needs 'opts' with at least 2 options")
            elif isinstance(q.get("a"), bool) or not isinstance(q.get("a"), int) or not 0 <= q["a"] < len(opts):
                errs.append(f"{where}: 'a' must be the index of the correct option, 0..{len(opts) - 1} (got {q.get('a')!r})")
        elif q.get("type") == "ox":
            a = str(q.get("a")).strip().lower()
            if a in OX_TRUE:
                q["a"] = "O"
            elif a in OX_FALSE:
                q["a"] = "X"
            else:
                errs.append(f"{where}: a true/false answer 'a' must be \"O\" (true) or \"X\" (false) (got {q.get('a')!r})")
        else:
            errs.append(f"{where}: 'type' must be \"mc\" or \"ox\" (got {q.get('type')!r})")
    card_ids, attached = {}, {}
    for ci, ch in enumerate(course["chapters"]):
        if not ch.get("name"):
            errs.append(f"chapter {ci + 1}: missing 'name'")
        if not isinstance(ch.get("cards"), list) or not ch["cards"]:
            errs.append(f"chapter {ci + 1} ({ch.get('name', '')}): no 'cards'")
            continue
        for c in ch["cards"]:
            cid = c.get("id")
            if not cid:
                errs.append(f"chapter {ci + 1}: a card has no 'id'")
                continue
            if cid in card_ids:
                errs.append(f"card id '{cid}' is used twice (ids must be unique across the course)")
            card_ids[cid] = True
            for f in ("title", "one"):
                if not c.get(f):
                    errs.append(f"card {cid}: missing '{f}'")
            for qid in (c.get("qids") if isinstance(c.get("qids", []), list) else []):
                if qid not in bank_ids:
                    errs.append(f"card {cid}: question '{qid}' is not in the bank (the quiz would crash)")
                attached.setdefault(qid, []).append(cid)
            if not isinstance(c.get("vis", []), list):
                errs.append(f"card {cid}: 'vis' must be a list of diagrams")
                continue
            if not isinstance(c.get("qids", []), list):
                errs.append(f"card {cid}: 'qids' must be a list of question ids")
            for vi, v in enumerate(c.get("vis", [])):
                where = f"card {cid}, diagram {vi + 1}"
                if not isinstance(v, dict):
                    errs.append(f"{where}: each diagram is an object like {{\"type\": \"steps\", ...}}")
                    continue
                tp = v.get("type")
                if tp not in REQUIRED:
                    errs.append(f"{where}: unknown diagram type {tp!r} (allowed: {sorted(REQUIRED)})")
                    continue
                for f in REQUIRED[tp]:
                    if f not in v:
                        errs.append(f"{where} ({tp}): missing required field '{f}'")
                for k in v.get("say", {}):
                    try:
                        int(k)
                    except (TypeError, ValueError):
                        errs.append(f"{where}: 'say' keys must be step numbers like \"0\" or \"-1\" (got {k!r})")
                if tp == "vs" and v.get("win") not in (None, "left", "right"):
                    errs.append(f"{where}: 'win' must be \"left\" or \"right\"")
                if tp == "vs" and any(len(r) != 3 for r in v.get("rows", [])):
                    errs.append(f"{where}: every vs row is [label, left text, right text]")
                if tp == "bars":
                    if any(len(x) != 2 or not isinstance(x[1], (int, float)) for x in v.get("items", [])):
                        errs.append(f"{where}: bars items are [label, number]")
                    elif v.get("star") is not None and (isinstance(v["star"], bool) or not (isinstance(v["star"], int) and 0 <= v["star"] < len(v["items"]))):
                        errs.append(f"{where}: 'star' must be the index of a bar")
                if tp == "flow" and any(len(b) < 2 or (len(b) > 2 and b[2] not in ("good", "bad", "")) for b in v.get("branch", [])):
                    errs.append(f"{where}: each branch is [condition, outcome] or [condition, outcome, \"good\" | \"bad\"]")
                if tp == "table" and any(len(r) != len(v.get("head", [])) for r in v.get("rows", [])):
                    errs.append(f"{where}: every table row needs as many cells as 'head'")
                if tp == "steps" and any(not isinstance(x, list) or len(x) != 2 for x in v.get("items", [])):
                    errs.append(f"{where}: steps items are [name, description] (use \"\" for no description)")
                if tp in ("big", "timeline") and any(not isinstance(x, list) or len(x) != 2 for x in v.get("items", [])):
                    errs.append(f"{where}: {tp} items are [headline, text] pairs")
                if tp == "tiles" and any(not isinstance(x, str) for x in v.get("items", [])):
                    errs.append(f"{where}: tiles items are plain strings")
                if tp == "groups" and any(not isinstance(g, dict) or not g.get("name") or not isinstance(g.get("items"), list)
                                          for g in v.get("groups", [])):
                    errs.append(f"{where}: each group is {{\"name\": ..., \"items\": [...]}} (items may be empty)")
                if tp == "rows" and any(not isinstance(r, list) or len(r) != 2 or not isinstance(r[1], list) for r in v.get("rows", [])):
                    errs.append(f"{where}: rows are [label, [chain item, chain item, ...]]")
                for f in ("items", "groups", "rows", "nodes", "head"):
                    if f in v and not isinstance(v[f], list):
                        errs.append(f"{where}: '{f}' must be a list")
    for qid, cs in attached.items():
        if len(cs) > 1:
            errs.append(f"question '{qid}' is attached to several cards {cs}; attach each question to exactly one card")
    return errs


def print_strings(lang):
    ui, ph, sym, has = pack(lang)
    print(json.dumps({"ui": ui, "phrases": ph, "symbols": [list(x) for x in sym]}, ensure_ascii=False, indent=1))
    if not has:
        print(f"(no '{lang}' pack: these are the English strings to translate)", file=sys.stderr)


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
    errs = validate(course)
    cdir = pathlib.Path(course_path).resolve().parent
    out = pathlib.Path(out_dir).resolve() if out_dir else cdir
    lang = course.get("lang", "en")
    ui, ph, sym, has_pack = pack(lang)
    tpl = TEMPLATE.read_text(encoding="utf-8")
    template_keys = set(re.findall(r'T\("([A-Za-z0-9]+)"', tpl)) - {"sayWrongPrefix"}
    warn = []
    if not has_pack:
        # start from no English at all: "_one" singulars are optional (the translated plural form is used instead)
        ui = {k: v for k, v in ui.items() if not k.endswith("_one")}
        need_ui = template_keys | {"oxKeysTrue", "oxKeysFalse"}
        miss_ui = sorted(k for k in need_ui if k not in course.get("ui", {}))
        miss_ph = sorted(k for k in PHRASES["en"] if k not in course.get("phrases", {}))
        if (miss_ui or miss_ph) and not course.get("allowEnglishFallback"):
            errs.append(f"there is no '{lang}' language pack, and the course does not translate "
                        f"{len(miss_ui)} UI strings and {len(miss_ph)} narration phrases (e.g. {(miss_ui + miss_ph)[:6]}). "
                        f"Run `python3 scripts/build.py --print-strings en > strings.json`, translate the values, and put them "
                        f"in the course as \"ui\", \"phrases\" and \"symbols\" (or set \"allowEnglishFallback\": true).")
        elif miss_ui or miss_ph:
            warn.append(f"no '{lang}' pack: {len(miss_ui) + len(miss_ph)} strings fall back to English (allowEnglishFallback)")
    if errs:
        raise CourseError("\n".join(errs))
    (out / "build").mkdir(parents=True, exist_ok=True)
    ui.update(course.get("ui", {}))
    ph.update(course.get("phrases", {}))
    ui["sayWrongPrefix"] = ph["wrongPrefix"]          # one source for the spoken wrong-answer prefix
    lacking = sorted(k for k in template_keys if k not in ui)
    if lacking:
        warn.append(f"UI strings missing for '{lang}': {lacking} (add them to the course's \"ui\")")
    sym = [tuple(x) for x in course.get("symbols", [])] + sym
    say = Speaker(lang, course.get("names", {}), ph, sym)
    voice = dict({"engine": "browser"}, **course.get("voice", {}))
    vkey = f"{voice['engine']}:{voice.get('voice', '')}"

    bank = [dict(q) for q in course.get("bank", [])]
    if course.get("shuffleOptions", True):
        balance_options(bank, course.get("id", "course"))
    bank_by = {q["id"]: q for q in bank}
    problems, script, used = list(warn), [], {}
    risky = re.compile(r"[<>=✗○→↔↑↓÷×~\"+−()\[\]]|\b[Vv][Ss]\b\.?" + (r"|[A-Za-z]{2,}" if say.lang in NON_LATIN else ""))
    allow = re.compile("|".join(map(re.escape, course.get("allowInNarration", []))) or r"(?!)")

    chapters = []
    for ci, ch in enumerate(course["chapters"]):
        n = len(ch["cards"])
        cname = say(ch["name"])
        intro = ch.get("sayIntro") or ph["intro"].format(name=cname, sub=end(say(ch.get("sub", ""))) if ch.get("sub") else "", n=n).replace("  ", " ")
        outro = ch.get("sayOutro") or ph["outro"].format(name=cname)
        for k, line in (("intro", intro), ("outro", outro)):
            if risky.search(allow.sub("", line)):
                problems.append(f"chapter {ci + 1} {k}: check how this reads aloud: {line}")
        script.append(f"\n######## {ch['name']}\n[intro] {intro}")
        cards = []
        for c in ch["cards"]:
            beats = card_beats(c, say)
            for qid in c.get("qids", []):
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
    script.append("\n######## Fixed lines (quiz feedback, results, voice sample)")
    script += [f"  [{k}] {ph[k]}" for k in fixed_keys]
    script.append("\n######## Quiz questions and wrong-answer lines")
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
        script.append(f"  {qid} [question] {sq}")
        if q["type"] == "mc":
            script.append(f"  {qid} [wrong answer] {ph['wrongPrefix'] + q['sayA']}")
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
    # Gate A input: each card with the questions attached to it (correct answer marked)
    rev = []
    plain = lambda x: html.unescape(re.sub(r"<[^>]+>", "", str(x))).replace("**", "")
    for ch in course["chapters"]:
        rev.append(f"\n######## {ch['name']}")
        for c in ch["cards"]:
            rev.append(f"\n=== CARD {c['id']} · {c['title']}")
            rev.append(json.dumps({k: c[k] for k in ("one", "vis", "hook", "terms", "ex") if k in c}, ensure_ascii=False))
            for qid in c.get("qids", []):
                q = bank_by[qid]
                if q["type"] == "mc":
                    rev.append(f"  Q {qid} [multiple choice] {plain(q['q'])}\n     options: {' / '.join(map(plain, q['opts']))}"
                               f"\n     correct: {plain(q['opts'][q['a']])}\n     explanation: {plain(q.get('exp', ''))}")
                else:
                    rev.append(f"  Q {qid} [true/false] {plain(q['q'])}\n     correct: {'true' if q['a'] == 'O' else 'false'}"
                               f"\n     explanation: {plain(q.get('exp', ''))}")
    (out / "build" / "review.txt").write_text("\n".join(rev), encoding="utf-8")
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
    if voice["engine"] != "browser" and embed_audio and not audio:
        print(f"note: no recorded clips in {clip_dir} yet, so this build uses the browser voice. Record with "
              f"tts_render.py {out}, then tts_trim.py, then rebuild.")
    if problems:
        print(f"\nto check ({len(problems)}):")
        for p in problems:
            print(" -", p)
    return {"problems": problems, "lines": len(lines), "audio": len(audio)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--no-audio", action="store_true", help="do not embed recorded clips")
    ap.add_argument("--print-strings", nargs="?", const="en", metavar="LANG", help="print every translatable string as JSON")
    a = ap.parse_args()
    if a.print_strings:
        print_strings(a.print_strings)
        sys.exit(0)
    if not a.course:
        ap.error("give a course file")
    try:
        build(a.course, a.out, not a.no_audio)
    except CourseError as e:
        print("The course has errors that would break the app:\n- " + str(e).replace("\n", "\n- "), file=sys.stderr)
        sys.exit(1)
