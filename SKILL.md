---
name: conceptcast
description: Turn study material (lecture notes, PDFs, slides, textbook chapters) into a narrated, auto-playing visual lesson app — one concept per screen, built up beat by beat with diagrams, a memory hook and the exact answer terms, then recall quizzes that replay what was missed. Works for any subject and language, with a choice of voices (browser, Microsoft neural, Gemini, OpenAI, ElevenLabs, local open-source, macOS). Use when someone wants passive, low-effort, low-attention or ADHD-friendly studying, "press play and just watch" learning, a narrated study app or exam-cram material from their notes, or asks to make another ConceptCast.
---

# ConceptCast

A ConceptCast is one self-contained HTML file. The learner presses play once and watches: each
concept appears as its own scene, built up piece by piece (title → one-line idea → diagram items →
memory hook → exact terms → example) while a voice reads each piece. After each chapter comes a
recall quiz (one question per concept); missed concepts can be replayed and the exact missed
questions re-asked.

It was designed for a tired, distracted learner the night before an exam. Every design choice
serves that: one idea per screen, nothing to click until the quiz, exact exam wording, and audio
that never stalls.

Read `references/method.md` once before the first build; it explains why each step exists.
The full pipeline is drawn in `diagram/pipeline.svg`.

## Step 0 — Ask first (one AskUserQuestion call, before any work)

Ask these together; offer a recommended default for each:

1. **Material and scope.** Which files are the course, and which are not (other classes, excluded
   sections)? Is there an exam with topics, weights, or a date?
2. **Language** of the material and of the exam answers. Exact terms in that language matter more
   than anything else.
3. **Where it will be used.** Device and browser (e.g. Mac + Safari, iPhone, Windows + Chrome).
   This decides how you test (Step 7).
4. **Voice.** Offer these options (details and setup: `references/tts-options.md`):
   - **Microsoft neural voices** via edge-tts. Free, no key, very natural, needs internet while
     recording. Recommended default.
   - **Gemini TTS** or **OpenAI TTS**. Expressive, needs an API key, pay per use.
   - **ElevenLabs.** Premium quality, needs an API key, paid.
   - **Local open-source.** Piper, Kokoro, MeloTTS, or Qwen3-TTS on Apple Silicon. Offline and
     private, but slower, needs a model download (ask before any download over ~1 GB), and
     language coverage varies.
   - **macOS voices** (`say`). Offline, instant; "Premium" voices are decent.
   - **Browser voice only.** No recording, smallest file, but robotic.

Then check the folder for an existing course file or notes the user may have left.

## Step 1 — Ingest

- Convert PDFs, slides and documents to Markdown (e.g. `markitdown file.pdf -o file.md`).
- Transcribe image-only pages: read each page image directly and write the text into the Markdown.
- Check extraction against the rendered page where text looks garbled (doubled glyphs, broken
  tables), e.g. with `pdftotext -layout`.
- Keep out-of-scope files out, and say which files you used.

The Markdown notes are now the **single source of truth**; every later claim must trace to them.

## Step 2 — Question bank

Write multiple-choice (`mc`) and true/false (`ox`) questions in the notes' own wording. Each
question gets:

- `exp`: an explanation that does not refer to option numbers, because options are shuffled;
- `ref`: where in the notes the answer is.

Aim for 2–4 questions per concept. Format: `references/course-schema.md`.

## Step 3 — Concept cards

Write `course.json` (or `course.py` defining `COURSE = {...}`): chapters → cards → diagrams.

- **One concept per card.** Split a card when it needs more than ~3 diagrams or ~12 beats.
- **`one`:** one sentence. Put the key words in `**bold**`; they become highlighter marks.
- **`terms`:** the exact answer terms, copied from the notes.
- **`hook`:** a short memory line. It may be playful, but it must not assert anything the notes
  don't say.
- **Diagrams:** pick the type that matches the shape of the idea. See
  `references/visual-types.md`; e.g. a comparison is `vs`, a process is `flow`, reasons are `steps`.
- **Tags:** mark outside facts `[extra]` and readings of a figure `[interpretation]` on screen and
  in the narration.
- **Attach questions:** attach every bank question to exactly one card (`qids`), on the card
  that teaches its answer.

**Gate A — independent content review.** Spawn a fresh subagent with the prompt in
`references/verification.md`. It checks every claim against the notes, plus coverage: could
someone who watched only that card answer each of its questions? Apply the fixes. Add any fact
that a question needs but the card doesn't teach.

## Step 4 — Build and review the narration

```bash
python3 scripts/build.py path/to/course.json
```

This writes:

- `<id>.html`: the app.
- `build/narration.txt`: every spoken line.
- `build/voice_lines.json`: the lines to record.

It also lists lines that may read badly aloud (symbols, stray Latin letters in non-Latin text),
questions not attached to any card, and template syntax errors.

Read `build/narration.txt` end to end. Fix awkward lines with overrides (`sayOne`, `sayHook`,
`say: {index: text}` on a diagram; see `references/narration.md`), and teach pronunciations
through `names`. Rebuild until clean.

## Step 5 — Voice (skip for browser-only)

1. **Audition.** Put 2–3 options in `voice.candidates`, then run:
   ```bash
   uv run --with edge-tts python scripts/tts_render.py COURSE_DIR --audition
   ```
   This records the same line in each voice and plays them on the speakers.

   **Gate B:** the learner picks a voice. Never start a long recording without this sign-off.
2. **Record everything:**
   ```bash
   uv run --with edge-tts python scripts/tts_render.py COURSE_DIR
   ```
   It caches clips by text, so a re-run records only changed lines. Expect about 1 minute per
   100 lines with edge-tts. If a provider fails twice the same way, stop and fix the cause (key,
   model name, network); don't retry blindly.
3. **Trim silence:**
   ```bash
   python3 scripts/tts_trim.py COURSE_DIR
   ```
   It trims padding and proves no speech was cut.
4. **Check every clip:**
   ```bash
   python3 scripts/tts_check.py COURSE_DIR
   ```
   One-word lines read "slow" and English inside other languages reads "fast"; that is normal.
   Anything else, listen to it.
5. **Rebuild** with `python3 scripts/build.py course.json`, which embeds the clips. The file
   grows by about 0.4 MB per spoken minute.

## Step 6 — Build

`build.py` produces the final single file. The player handles everything else:

- the voice fallback chain (recorded clip → browser voice → reading timer);
- speed 0.9–1.5×, keyboard controls, saved progress;
- replaying missed concepts and re-asking the exact missed questions;
- light and dark themes, and phone layouts.

## Step 7 — Verify like the learner (Gate C)

- **Mechanical, all items, never samples.** On macOS, run `swift scripts/webkit_test.swift app.html`
  (Safari's engine, silent). It covers:
  - every beat renders;
  - narrated playback advances, ←/→ move exactly one beat, and pause stops audio;
  - voice-off mode advances;
  - the first chapter's quiz grades right;
  - results are saved.

  For other browsers, drive the page with `window.__player` (`jump`, `state`, `cards`, `voice`).
- **Through the learner's channel.** Open the file the way they will (double-click → their default
  browser). A hosted copy must be checked where it is hosted.
- **Independent refutation.** A fresh subagent tries to break it, using the refuter prompt in
  `references/verification.md`. It checks:
  - every clip ↔ its text;
  - every question graded both ways;
  - every beat rendered;
  - accuracy fixes actually applied.

  Fix what it finds and re-run its checks. The builder never signs off on its own work.
- **Clean up.** Stop servers, clear test progress (`localStorage` key
  `conceptcast-<id>-v1`), and leave no background processes running.

Deliver the absolute path of `<id>.html` and an `open` command. If the user also wants a hosted
copy, note size limits: recorded audio makes the file large.

## Files

| Path | What it is |
|---|---|
| `assets/player.html` | The app template (language-neutral; text comes from language packs) |
| `scripts/build.py` | course.json → app, narration script, voice line list, lint |
| `scripts/langpacks.py` | UI strings, narration phrases and spoken-symbol rules per language (en, ko). Add a language by copying `en` |
| `scripts/tts_render.py` | Record lines with the chosen engine; `--audition`, `--list-voices` |
| `scripts/tts_trim.py`, `scripts/tts_check.py` | Trim and check every clip |
| `scripts/webkit_test.swift` | Silent Safari-engine test of a built app (macOS) |
| `references/` | Method, course schema, diagram types, narration rules, TTS options, verification prompts |
| `examples/memory-basics/` | A small English course, built with a neural voice |
