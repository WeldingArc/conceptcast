# Course file schema

A course is one JSON file (`course.json`) or a Python file defining `COURSE = {...}`. Python is
handy for long courses: comments, trailing commas, no escaping of quotes. See
`examples/memory-basics/course.json`.

## Top level

```jsonc
{
  "id": "memory-basics",            // file name, storage key; letters, digits, dashes
  "title": "How Memory Works",
  "subtitle": "Midterm review",     // optional, shown after the title
  "lang": "en",                     // language pack: en, ko, or one you add
  "locale": "en-US",                // optional; browser voice locale (default from lang)
  "exam": { "date": "2026-11-02", "label": "Nov 2 (Mon) 9:00" },   // optional D-day chip
  "voice": { "engine": "edge", "voice": "en-US-AndrewMultilingualNeural", "label": "Andrew",
             "candidates": [ { "voice": "en-US-AvaMultilingualNeural" }, { "voice": "en-US-AndrewMultilingualNeural" } ] },
  "preferBrowserVoice": "Samantha|Ava",   // optional regex for the fallback browser voice
  "footer": "Covers chapters 1–4. Chapter 5 is not on the exam.",   // optional, home screen
  "names": { "Zajonc": "ZY-unts" },       // pronunciations: written form → spoken form
  "allowInNarration": ["SNS", "BTS"],     // tokens the narration lint should not flag
  "ui": { },                              // optional overrides of any UI string
  "phrases": { },                         // optional overrides of narration phrases
  "shuffleOptions": true,                 // balance correct-answer positions (default true)
  "chapters": [ ... ],
  "bank": [ ... ]
}
```

`voice.engine`: `edge`, `say`, `openai`, `gemini`, `elevenlabs`, `command`, or `browser`. Other
keys depend on the engine (`references/tts-options.md`). The clip cache is keyed by engine,
voice and text, so changing the voice re-records everything.

## Chapters

```jsonc
{
  "id": "ch1",
  "name": "How memory works",
  "sub": "Three stages, a small workbench, and a fast fade",   // one line under the chapter title
  "chips": ["Weeks 2–3", "6 questions · 18 points"],         // optional tags on intro and home
  "color": "#2F7A80",                                        // optional; muted, deep tones read best
  "sayIntro": "...", "sayOutro": "...",                      // optional narration overrides
  "cards": [ ... ]
}
```

## Cards (one concept each)

```jsonc
{
  "id": "m-stages",                       // unique across the course
  "title": "Three stages of memory",
  "one": "Every memory goes **in**, **stays**, and comes **back out**.",   // **bold** = highlighter
  "vis": [ { "type": "flow", ... } ],     // 1–3 diagrams; see visual-types.md
  "hook": "In, keep, out",                // memory line (may be playful; asserts nothing new)
  "terms": ["encoding", "storage", "retrieval"],   // exact answer terms; [] to skip the beat
  "ex": "Remembering a friend's name at a party is retrieval.",   // optional example
  "qids": ["q1"],                         // questions this card teaches (each question on one card)
  // optional narration overrides:
  "sayTitle": "...", "sayOne": "...", "sayHook": "...", "sayTerms": "...", "sayEx": "..."
}
```

Beat order: `title`, `one`, each diagram's beats, then `hook`, `terms`, `ex` (each only if
present). Cards with no questions are fine: overviews, maps, lists of topics.

## Questions

```jsonc
{ "id": "q1", "type": "mc",
  "q": "Which memory stage means getting stored information **back out**?",
  "opts": ["Retrieval", "Encoding", "Storage", "Consolidation"], "a": 0,
  "exp": "Retrieval is accessing stored information. Encoding puts it in; storage keeps it.",
  "ref": "Chapter 1 · Three stages of memory",
  "sayQ": "...", "sayA": "...",           // optional narration overrides (question, correct option)
  "fixedOrder": false }                   // true keeps options unshuffled (e.g. "all of the above")

{ "id": "q2", "type": "ox", "q": "Chunking lets working memory hold more ...", "a": "O",   // "O" = true, "X" = false
  "exp": "...", "ref": "..." }
```

- Write the correct option anywhere. `shuffleOptions` moves it so that positions 1–4 are used
  about equally, the same way on every build.
- `exp` must not say "option 2". Say the answer itself.
- The recall quiz asks one question per card. It prefers unseen questions, then
  previously-missed ones; a re-check asks the exact questions just missed.

## Output files

| Path | Purpose |
|---|---|
| `<id>.html` | The app. Double-click to open |
| `<id>.body.html` | Same page without `<html>/<head>`, for hosts that add their own wrapper |
| `build/narration.txt` | Every spoken line, numbered by beat, for review |
| `build/voice_lines.json` | `{clip_id: text}` plus the voice settings, for `tts_render.py` |
| `voice/raw/` | Recorded clips as delivered by the engine, plus `manifest.json` |
| `voice/clips/` | Trimmed clips that get embedded, plus `manifest.json` |
