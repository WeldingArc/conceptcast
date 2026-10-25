# Course file schema

A course is one JSON file (`course.json`) or a Python file defining `COURSE = {...}`. Python is
handy for long courses: comments, trailing commas, no escaping of quotes. See
`examples/memory-basics/course.json`.

Keep each course in its own folder (`COURSE_DIR`). The build writes the app and its working
files there, and the voice scripts take that folder as their argument. With `build.py --out DIR`,
`DIR` becomes the COURSE_DIR instead.

`build.py` validates the file first. Anything that would break the app is an error (exit 1),
listed one per line: missing required fields, unknown diagram types, duplicate ids, question ids
that aren't in the bank, questions attached to two cards, bad answers.

## Top level

```jsonc
{
  "id": "memory-basics",            // file name, storage key; letters, digits, dashes
  "title": "How Memory Works",
  "subtitle": "Midterm review",     // optional, shown after the title
  "lang": "en",                     // built-in packs: en, ko. Any other language: see "Other languages" below
  "locale": "en-US",                // optional; browser voice locale (default from lang)
  "exam": { "date": "2026-11-02", "label": "Nov 2 (Mon) 9:00" },   // optional D-day chip
  "voice": { "engine": "edge", "voice": "en-US-AndrewMultilingualNeural", "label": "Andrew",
             "candidates": [ { "voice": "en-US-AvaMultilingualNeural" }, { "voice": "en-US-AndrewMultilingualNeural" } ] },
  "preferBrowserVoice": "Samantha|Ava",   // optional regex for the fallback browser voice
  "footer": "Covers chapters 1–4. Chapter 5 is not on the exam.",   // optional, home screen
  "names": { "Zajonc": "ZY-unts" },       // pronunciations: written form → spoken form
  "allowInNarration": ["SNS", "BTS"],     // tokens the narration lint should not flag
  "ui": { },                              // overrides of on-screen strings (required for a language without a pack)
  "phrases": { },                         // overrides of narration phrases (same)
  "symbols": [["↑", " sube"], ["=", ", es decir, "]],   // optional extra spoken-symbol rules, applied first
  "allowEnglishFallback": false,          // true = build a language without a pack even if strings are missing
  "shuffleOptions": true,                 // balance correct-answer positions (default true)
  "chapters": [ ... ],
  "bank": [ ... ]
}
```

`voice.engine`: `edge`, `say`, `openai`, `gemini`, `elevenlabs`, `command`, or `browser`. Other
keys depend on the engine (`references/tts-options.md`). The clip cache is keyed by engine,
voice and text, so changing the voice re-records everything.

Required: `chapters`. Set `id` (it names the output file and the saved progress; default "course") and `title` too. `bank` may be empty, but then there is no quiz.

## Other languages

1. Run `python3 scripts/build.py --print-strings en > strings.json`. It prints every on-screen
   string (`ui`, ~80 keys), every narration phrase (`phrases`, ~25 keys) and the spoken-symbol
   rules (`symbols`).
2. Translate the values; keep the `{placeholders}`.
3. Put the result in the course file.

Keys ending in `_one` are the singular form used when the count is 1 (e.g. `conceptsN_one`: "1
concept"); omit them if your language doesn't inflect. `oxKeysTrue` / `oxKeysFalse` are the
keyboard letters for true/false, e.g. `"VO"` / `"FX"` for Spanish *verdadero/falso*.

Without a pack the build refuses to run until every string is translated, because otherwise the
app comes out half in English. Symbols default to punctuation-only rules (no English words);
add `symbols` for words like "up" or "that is" in your language.

## Chapters

```jsonc
{
  "id": "ch1",                                               // optional (default ch1, ch2, …)
  "name": "How memory works",                                // required
  "sub": "Three stages, a small workbench, and a fast fade",   // one line under the chapter title
  "chips": ["Unit 1", "Exam: 5 questions"],                  // optional tags on intro and home
  "color": "#2F7A80",                                        // optional; muted, deep tones read best
  "sayIntro": "...", "sayOutro": "...",                      // optional narration overrides
  "cards": [ ... ]                                           // required, at least one
}
```

## Cards (one concept each)

```jsonc
{
  "id": "m-stages",                       // required, unique across the course
  "title": "Three stages of memory",      // required
  "one": "Every memory goes **in**, **stays**, and comes **back out**.",   // required; **bold** = highlighter
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

The hook, terms and example beats are spoken with a prefix from the language pack ("Remember it
like this.", "Use these exact terms.", "Example from the notes."). `sayHook`, `sayTerms` and
`sayEx` replace only the text after that prefix. `sayTitle` and `sayOne` replace the whole line.
To change a prefix, override `phrases.hook`, `phrases.terms` or `phrases.ex`.

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

Required: `id` (unique), `type` (`mc` or `ox`), `q`. For `mc`: `opts` (2 or more; 5+ is fine) and
`a` (the 0-based index of the correct option). For `ox`: `a` is `"O"` or `"X"`; `true`/`false`,
`"T"`/`"F"` are accepted and converted.

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
| `build/narration.txt` | Every spoken line for review: concept beats, then fixed lines, then quiz questions and wrong-answer lines |
| `build/review.txt` | Each card with its attached questions and correct answers: the input for the Gate A review |
| `build/voice_lines.json` | `{clip_id: text}` plus the voice settings, for `tts_render.py` |
| `voice/raw/` | Recorded clips as delivered by the engine, plus `manifest.json` |
| `voice/clips/` | Trimmed clips that get embedded, plus `manifest.json` |
