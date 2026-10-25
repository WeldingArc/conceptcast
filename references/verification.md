# Verification

Two independent reviews and one mechanical test run stand between a draft and the learner. The
builder never signs off on its own work: spawn a fresh subagent for each review, give it the
stakes and the paths, and ask for structured output with a confidence per item.

## Gate A: content review (after cards are written, before narration review)

Prompt template (fill in the brackets):

```
You are checking study content for [learner, exam, date]. Grading requires the exact
terminology from the notes. The learner will passively watch and listen to these concept cards,
so anything wrong, reversed or unsupported will be memorized as fact and cost points.
Do not guess; when unsure, put it in needs_review.

Source of truth: [paths to the Markdown notes]. Known extraction issues: [e.g. doubled glyphs;
compare with the rendered PDF page]. Excluded from scope: [sections]. Spellings that look wrong
but are the notes' own: [list].

Material: [course.json path]. A dump of each card with its attached questions (options,
correct answer, explanation): [path].

JOB 1, accuracy: check every claim in every card (one, diagram items, hook, ex, terms) against
the notes. Flag (a) factual errors: reversals, wrong numbers, names or pairings; (b) claims the
notes don't support (memory hooks are fine if they assert nothing new); (c) wording that
deviates from the notes' exact terms; (d) excluded material. Pay special attention to: [numbers,
lists, look-alike terms, the things you are least sure of].

JOB 2, coverage: for each attached question, could someone who watched ONLY that card answer
it? If not, give the minimal missing fact, in the notes' wording.

Output one JSON object:
{"accuracy":[{"card","field","card_says","notes_say","problem","fix","confidence"}],
 "coverage":[{"qid","card","answerable","missing_fact","confidence"}],
 "needs_review":[...]}
Report only; do not edit files.
```

To produce the dump, iterate the course's cards and print each card's JSON followed by its
questions with options, correct answer and explanation.

## Mechanical checks (every item, never samples)

| Check | How |
|---|---|
| Every question attached to exactly one card; no missing question ids | `build.py` output |
| Narration lint clean, or every flag reviewed | `build.py` output, then `build/narration.txt` |
| Template has no syntax errors | `build.py` (runs `node --check` when Node is installed) |
| Every clip recorded, trimmed with no speech cut, sane rate, loudness and gaps | `tts_trim.py`, `tts_check.py` |
| Every clip matches its line | rebuild and confirm 0 lines without a clip; the clip id is a hash of voice and text |
| Every beat renders (one active diagram, a highlighted item, recap on recap beats, no sideways overflow) | `swift scripts/webkit_test.swift app.html` (macOS, Safari engine) |
| Playback advances on its own; ←/→ move one beat; pause stops audio; voice-off advances | same |
| Quiz grades correct answers as correct; results saved and shown | same (chapter 1). For all questions, see the refuter |

Test hook for other browsers: `window.__player.jump(cardId, beat)`, `.state()`, `.cards()`,
`.voice()`. Mute audio by wrapping `HTMLMediaElement.prototype.play` (set `volume`) and stub
`speechSynthesis.speak` before interacting.

Hidden or background windows throttle timers and pause CSS transitions. Read timing from event
timestamps, and take screenshots with transitions disabled.

## Through the learner's channel

- Open the file exactly as the learner will: double-click opens their default browser. On a Mac
  that is usually Safari.
- If it is hosted, check the hosted copy, not only the local file.
- Phone use needs a phone-width check (375 px) and a real tap to start audio. Browsers only
  allow sound after a user gesture; the first clip starts from the play tap.
- A saved setting from an older build can change behaviour. Test with fresh storage *and* with
  storage left by the previous version.

## Gate C: refuter (after everything passes for you)

Prompt template:

```
Your only job is to REFUTE the claim that this study app is correct and done. Be adversarial and
mechanical: check every item, not samples. Report only; do not edit files.

Context: [learner, exam, how they will use it: device and browser, voice on].
Files: app [path] (embedded data: `var DATA = {...};`), course [path], notes [paths],
clip manifests [voice/clips/manifest.json], narration [build/narration.txt].

Checks:
1. Mapping: every beat, intro/outro, question line and wrong-answer line has a clip in DATA.audio.
   Each clip's manifest text equals the app's text, and the base64 equals the file on disk.
   The wrong-answer line names the CORRECT option for every question.
2. Audio: re-run tts_check and explain each flag.
3. Behaviour in [the learner's browser engine]:
   - every beat renders;
   - playback advances on clip end; ←/→ move one beat; Space pauses;
   - speed applies to the playing clip;
   - every question graded right and wrong, with the right explanation;
   - replay of missed concepts, then a re-check that asks the exact missed questions;
   - Esc and Home stop audio;
   - forced playback failure falls back to the browser voice and keeps advancing;
   - storage left by an older version doesn't change the voice.
   Keep everything silent.
4. Content: every accuracy fix from Gate A is applied (fixed / partly / not, item by item).
Output: verdict (REFUTED / NOT REFUTED); failures with repro steps, severity and confidence;
counts for every mechanical check; anything you could not check.
```

Fix what it finds, re-run its specific checks, and only then report done. In the report, list
what could not be verified, in plain words.

## Hygiene

- Stop any local server you started, and leave no background processes running (`pgrep`).
- Clear test progress: `localStorage` key `conceptcast-<id>-v1`.
- Never let tests play audio out loud unless the learner asked for a sample.
