# Diagram types

Every card has 1–3 diagrams (`"vis": [...]`). A diagram reveals one item per beat: the current
item is ringed, earlier items dim, and the narrator reads the item. Pick the type from the
**shape of the idea**, not for variety.

## Which type?

| The idea is… | Use | Example |
|---|---|---|
| a set of named things, no order | `tiles` | 9 basic needs; topics listed only as headings |
| things sorted into categories | `groups` | 4 categories of attraction factors; 5 power bases |
| reasons, features, or a procedure in order | `steps` | 5 reasons similarity attracts; 3 steps of retrieval practice |
| A against B on the same dimensions | `vs` | massed vs spaced practice; logical vs emotional appeal |
| a causal chain or process | `flow` | frustration → bad feeling → appraisal → aggression |
| a process with a fork | `flow` + `branch` | appraisal → (mitigating cue → no aggression \| none → aggression) |
| a before → during → after transformation | `rows` | classical conditioning; chunking 9 letters → 3 chunks |
| quantities to compare | `bars` | obedience rate by distance; forgetting by delay |
| one or two headline numbers or verdicts | `big` | "65%" of participants; "7 ± 2" items |
| three-way relations with signs | `triangle` | balance theory (P–O–X) |
| a ratio that must be equal on both sides | `balance` | equity theory |
| studies or events in sequence | `timeline` (or `steps`) | experiment → longitudinal → meta-analysis |
| a famous line worth remembering verbatim | `quote` | "the banality of evil" |
| a 2-D lookup (condition × outcome) | `table` | audience knowledge × one- vs two-sided message |
| a classic confusion or exception | `warn` | "negative reinforcement is not punishment" |
| a definition the exam wants word for word | `def` | the notes' exact definition of "frustration" |

Rules of thumb:

- **Cap a diagram at about 6 items.** More than that, split it or move the extras to a `tiles` overview.
- **Put the exact definition in `def`,** keep `one` conversational, and copy the notes' wording into `def`.
- **Use `warn` sparingly.** One per card at most; it is the "don't lose a point here" moment.
- **For `steps` and `timeline`, number only real sequences.** Use `groups` for unordered sets.

## Fields and narration

Item index `-1` is the diagram's intro beat (its title, or the two names in `vs`). Override any
beat's narration with `"say": {"index": "text"}`, using the indices listed here.

### tiles
```json
{ "type": "tiles", "title": "Optional title", "cols": 3, "items": ["One", "Two", "Three"] }
```
Beats: `-1` title (if any), then `0..n-1` one per tile. On phones, `cols` falls to 2.

### groups
```json
{ "type": "groups", "groups": [ { "name": "Category", "tag": "short label", "items": ["member", "member"] } ] }
```
Beats: one per group: name, tag (if longer than one character), then its items.

### steps
```json
{ "type": "steps", "title": "Why it works (3 reasons)", "items": [["Name", "one-line description"], ["Name", ""]] }
```
Beats: `-1` title, then "First. Name. Description." per step.

### vs
```json
{ "type": "vs", "left": "Massed", "right": "Spaced", "win": "right", "winText": "Lasts longer",
  "rows": [["Row label", "left cell", "right cell"], ["", "left only", ""]] }
```
Beats: `-1` "Massed versus Spaced", `0..n-1` one per row (empty cells are skipped), then `n` the
winner badge (only if `win` is set). Text in parentheses is dropped from the names when spoken.

### flow (+ branch)
```json
{ "type": "flow", "nodes": ["Cause", "Middle step", "Result"],
  "branch": [["If this", "then this outcome", "good"], ["Otherwise", "this outcome", "bad"]] }
```
Beats: one per node, then one per branch (index `nodes.length + j`). The last node is
emphasized. `good`/`bad` colour the branch.

### rows
```json
{ "type": "rows", "title": "Classical conditioning",
  "rows": [["Before", ["UCS (food)", "UCR (salivation)"]], ["After", ["CS (bell)", "CR (salivation)"]]] }
```
Beats: `-1` title, then one per row. Abbreviations usually need a `say` override.

### bars
```json
{ "type": "bars", "title": "Obedience by distance", "unit": "%", "max": 100,
  "items": [["Remote", 65], ["Voice", 62.5], ["Proximity", 40], ["Touch", 30]], "star": 0, "starText": "highest" }
```
Beats: `-1` title, then one per bar (the value counts up), then `items.length` for the star (if
`star` is set). Bar length is `value / max`.

### big
```json
{ "type": "big", "items": [["65%", "26 of 40 went to 450 V"], ["All", "went to 300 V"]] }
```
Beats: one per item. A number with an up-to-3-character suffix (`65%`, `26x`, `40 s`) counts up;
anything else shows as large text.

### triangle
```json
{ "type": "triangle", "p": "Me", "o": "Someone I like", "x": "What they like", "caption": "All three must fit" }
```
Beats: `0` P–O edge, `1` O–X edge, `2` P–X edge (the induced relation, gold), `3` caption.
Override all three edge lines with `say`; the generic wording is minimal.

### balance
```json
{ "type": "balance", "left": "Me", "right": "Partner", "top": "Rewards", "bottom": "Costs", "caption": "Equal ratios feel fair" }
```
Beats: `0` left pan (beam tilts), `1` right pan (beam levels), `2` "=" and caption.

### timeline
```json
{ "type": "timeline", "items": [["Josephson (1987)", "what it found"], ["Meta-analysis", "what it concluded"]] }
```
Beats: one per item.

### quote
```json
{ "type": "quote", "text": "The quote itself", "by": "Who (year)" }
```
Beat: `0`, "Who. Quote." Citations with a year in parentheses are not read aloud.

### table
```json
{ "type": "table", "head": ["Audience", "One-sided", "Two-sided"], "rows": [["Knows the topic", "", "✓"]] }
```
Beats: one per row; the header is always visible. Generic narration for 3+ columns is stiff, so
add `say` lines.

### warn
```json
{ "type": "warn", "text": "**Not the same as X.** Why it matters." }
```
Beat: `0`. Shown with a "Don't mix this up" label.

### def
```json
{ "type": "def", "term": "Frustration", "text": "The notes' exact definition, with the **key words** in bold" }
```
Beat: `0`, "Definition. Term. Text." Shown with a "use as written" label.
