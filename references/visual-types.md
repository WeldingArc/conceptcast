# Diagram types

Every card has 1–3 diagrams (`"vis": [...]`). A diagram reveals one item per beat: the current
item is ringed, earlier items dim, and the narrator reads the item. Pick the type from the
**shape of the idea**, not for variety.

## Which type?

| The idea is… | Use | Example |
|---|---|---|
| a set of named things, no order | `tiles` | the seven SI base units; topics listed only as headings |
| things sorted into categories | `groups` | macro- vs micronutrients; branches of government and their powers |
| reasons, features, or a procedure in order | `steps` | steps of the scientific method; three steps of retrieval practice |
| A against B on the same dimensions | `vs` | mitosis vs meiosis; massed vs spaced practice |
| a causal chain or process | `flow` | stimulus → receptor → nerve → brain |
| a process with a fork | `flow` + `branch` | glucose → glycolysis → (oxygen → aerobic respiration \| none → fermentation) |
| a before → during → after transformation | `rows` | classical conditioning; 9 letters → 3 chunks |
| quantities to compare | `bars` | forgetting by delay; ATP yield by pathway |
| one or two headline numbers or verdicts | `big` | "7 ± 2" items; "about 4" chunks |
| three-way relations with signs | `triangle` | balance theory (person, other, object) |
| a ratio that must be equal on both sides | `balance` | equity theory (outcomes ÷ inputs) |
| studies or events in sequence | `timeline` (or `steps`) | 1885 Ebbinghaus → 1956 Miller → 2001 Cowan |
| a famous line worth remembering verbatim | `quote` | a primary-source sentence the exam quotes |
| a 2-D lookup (condition × outcome) | `table` | audience × one- vs two-sided message; test delay × study method |
| a classic confusion or exception | `warn` | "negative reinforcement is not punishment" |
| a definition the exam wants word for word | `def` | the textbook's exact definition of the term |

Rules of thumb:

- **Cap a diagram at about 6 items.** Split anything longer, or move the extras to a `tiles` overview.
- **Use `def` for the exact definition** and keep `one` conversational. `def` copies the notes' wording.
- **Use `warn` sparingly,** one per card at most: it is the "don't lose a point here" moment.
- **Number only real sequences.** `steps` and `timeline` imply order; use `groups` for unordered sets.

## Fields and narration

Required fields are marked **required**. `build.py` stops with a clear error if one is missing.
Item index `-1` is the diagram's intro beat (its title, or the two names in `vs`). Override any
beat's narration with `"say": {"index": "text"}`, using the indices listed below. Only indices that
exist are accepted.

### tiles
```json
{ "type": "tiles", "title": "Optional title", "cols": 3, "items": ["One", "Two", "Three"] }
```
- **Required:** `items`.
- **Beats:** `-1` title (only if there is one), then `0..n-1`, one per tile.
- On phones, `cols` drops to 2.

### groups
```json
{ "type": "groups", "groups": [ { "name": "Category", "tag": "short label", "items": ["member", "member"] } ] }
```
- **Required:** `groups`, each with `name` and `items` (may be empty).
- **Beats:** one per group: its name, its tag (if longer than one character), then its items.

### steps
```json
{ "type": "steps", "title": "Why it works (3 reasons)", "items": [["Name", "one-line description"], ["Name", ""]] }
```
- **Required:** `items`, as `[name, description]` pairs. Use `""` for no description.
- **Beats:** `-1` title, then one per step ("First. Name. Description.").

### vs
```json
{ "type": "vs", "left": "Mitosis", "right": "Meiosis", "win": "right", "winText": "Makes gametes",
  "rows": [["Daughter cells", "2, identical", "4, all different"], ["", "left only", ""]] }
```
- **Required:** `left`, `right`, and `rows` as `[label, left text, right text]`.
- **Beats:**
  - `-1`: the intro, "Mitosis versus Meiosis";
  - `0..n-1`: one per row (empty cells are skipped);
  - `n`: the winner badge, only if `win` is `"left"` or `"right"`.
- Text in parentheses is dropped from the spoken names.

### flow (+ branch)
```json
{ "type": "flow", "nodes": ["Glucose", "Glycolysis", "Pyruvate"],
  "branch": [["With oxygen", "aerobic respiration", "good"], ["Without oxygen", "fermentation", "bad"]] }
```
- **Required:** `nodes`. Each branch is `[condition, outcome]` or `[condition, outcome, "good" | "bad"]`.
- **Beats:** one per node (index `0..`), then one per branch (index `nodes.length + j`).
- There is no `-1` beat.
- The last node is emphasized.

### rows
```json
{ "type": "rows", "title": "Classical conditioning",
  "rows": [["Before", ["UCS (food)", "UCR (salivation)"]], ["After", ["CS (bell)", "CR (salivation)"]]] }
```
- **Required:** `rows`, as `[label, [chain items]]`.
- **Beats:** `-1` title, then one per row.
- Abbreviations usually need a `say` override.

### bars
```json
{ "type": "bars", "title": "Savings when relearning", "unit": "%", "max": 100,
  "items": [["20 min", 58], ["1 day", 34], ["31 days", 21]], "star": 0, "starText": "highest" }
```
- **Required:** `items`, as `[label, number]`.
- **Optional:**
  - `unit`: default none; `"%"` is spoken as the language's "percent"; a word unit gets a space.
  - `max`: default the largest value.
  - `star`: the index of a bar to mark, with optional `starText`.
- **Beats:** `-1` title, then one per bar (the value counts up), then `items.length` for the star.

### big
```json
{ "type": "big", "items": [["7 ± 2", "items people can hold at once"], ["about 4", "a tighter estimate, in chunks"]] }
```
- **Required:** `items`, as `[headline, caption]`.
- **Beats:** one per item.
- A plain number with a suffix of up to 3 characters (`65%`, `26x`, `40 s`) counts up; anything
  else shows as large text.

### triangle
```json
{ "type": "triangle", "p": "Me", "o": "Someone I like", "x": "What they like", "caption": "All three must fit" }
```
- **Required:** `p`, `o`, `x`, `caption`.
- **Beats:** `0` P–O edge, `1` O–X edge, `2` P–X edge (the induced relation, drawn in gold), `3` caption.
- Write `say` lines for the three edges; the generic wording is minimal.

### balance
```json
{ "type": "balance", "left": "Me", "right": "Partner", "top": "Outcomes", "bottom": "Inputs", "caption": "Equal ratios feel fair" }
```
- **Required:** `left`, `right`, `top`, `bottom`, `caption`.
- **Beats:** `0` left pan (the beam tilts), `1` right pan (the beam levels), `2` "=" and the caption.

### timeline
```json
{ "type": "timeline", "items": [["1885 · Ebbinghaus", "the forgetting curve"], ["1956 · Miller", "7 ± 2"]] }
```
- **Required:** `items`, as `[label, text]`.
- **Beats:** one per item.

### quote
```json
{ "type": "quote", "text": "The quote itself", "by": "Who (year)" }
```
- **Required:** `text`, `by`.
- **Beat:** `0`, read as "Who. Quote."
- A year in parentheses is not read aloud.

### table
```json
{ "type": "table", "head": ["Tested after", "Reread", "Practiced recall"], "rows": [["5 minutes", "Ahead", "Behind"], ["1 week", "Behind", "Ahead"]] }
```
- **Required:** `head`, and `rows` with as many cells as `head`.
- **Beats:** one per row; the header is always visible.
- Generic narration for 3+ columns is stiff, so add `say` lines.

### warn
```json
{ "type": "warn", "text": "**Not the same as X.** Why it matters." }
```
- **Required:** `text`.
- **Beat:** `0`. Shown with the "Don't mix this up" label.

### def
```json
{ "type": "def", "term": "Retrieval", "text": "The notes' exact definition, with the **key words** in bold" }
```
- **Required:** `term`, `text`.
- **Beat:** `0`, read as "Definition. Term. Text."
- Shown with the "use as written" label.
