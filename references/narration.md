# Narration

Every beat has one spoken line. `build.py` generates it from the screen text, then cleans it for
the voice. You review `build/narration.txt` and override what reads badly. The learner hears every
line, often with eyes half-closed, so the narration is the lesson.

Everything the learner can hear is in `build/narration.txt`: the concept beats, then the fixed
lines (quiz feedback, results, voice sample), then every quiz question and wrong-answer line.

## How lines are generated

| Beat | Generated line (English pack) |
|---|---|
| title | the card title |
| one | the one-line idea |
| diagram items | see `visual-types.md` (e.g. "First. Name. Description.", "Massed: one long session.") |
| hook | "Remember it like this. " + hook |
| terms | "Use these exact terms. " + terms |
| ex | "Example from the notes. " + example |
| chapter intro / outro | phrase templates (`intro`, `outro` in the language pack) |
| quiz question | the question (true/false questions add "True or false?") |
| wrong answer | "Not quite. The answer is " + the correct option |

## Cleanup rules (automatic)

- Markup is stripped. `**bold**` is screen-only.
- Citations in parentheses are dropped (they are for the eye): a bare year "(2003)", or a name with a comma
  or "et al." before the year, e.g. "(Smith, 1999; Lee et al. 2004)". Other parentheses are read. If an aside
  like "(World War II, 1939)" should be spoken, write the line yourself with an override.
- In non-Latin-script languages, Latin-only glosses in parentheses are dropped (a Korean term
  followed by "(complementarity)" is read as the Korean term only). A parenthesis glued to a
  following particle is dropped too.
  Other parentheses are read as a short aside.
- Symbols become words or pauses, per language: `→ ↔ ↑ ↓ = vs & · / + ~`. Units and pages
  also become words: "450V", "p.3", "1~3".
- Apostrophes inside English words stay ("I'm", "can't"), so English quotes still read as English.
- `names` replaces written forms with spoken forms before reading, e.g.
  `"Zajonc": "ZY-unts"`. In a non-English course, map foreign names to their native-script
  spelling. Use it for every name a voice would mangle.

## The lint

`build.py` lists lines that may read badly: leftover symbols, brackets, and (in non-Latin
languages) runs of Latin letters. Add tokens that are fine aloud to `allowInNarration`
(e.g. "SNS", "BTS"). Treat every other flagged line as a to-do.

## Overrides

| Where | Field |
|---|---|
| card title / idea | `sayTitle`, `sayOne` (replace the whole line) |
| hook / terms / example | `sayHook`, `sayTerms`, `sayEx` (replace the text after the spoken prefix) |
| one diagram beat | `"say": {"2": "text"}` on the diagram, keyed by item index (`-1` = intro) |
| chapter intro / outro | `sayIntro`, `sayOutro` on the chapter |
| quiz question / correct option | `sayQ`, `sayA` on the question |
| phrase templates and prefixes | `"phrases": {...}` at course level (`build.py --print-strings` lists every key) |
| spoken symbols | `"symbols": [["↑", " sube"], ...]` at course level, applied before the pack's rules |

Write overrides when:

- **A symbol carries meaning.** "A > B" must become "A is greater than B". Generic rules cannot
  know which way round, so the four such quiz items in the first course got hand-written lines.
- **An abbreviation should be expanded:** "UCS" → "the unconditioned stimulus".
- **Screen shorthand doesn't work as speech.** "5% → 40%" becomes "from 5 percent to 40 percent".
- **A parenthetical is the important part,** like a definition in brackets.
- **A table has 3+ columns.** Generic narration is stiff.

Keep overrides faithful: they may rephrase, never add facts. Keep `[extra]` and
`[interpretation]` markers audible ("Note, as an interpretation, …").

## Style

- Short sentences. One idea per line. Periods, not semicolons.
- Read numbers the way they appear on screen.
- No filler ("So, basically…"); the pause between beats does that job.
- For quiz questions, read the question, not the options. The options are on screen, and reading
  four options aloud takes too long.
