# From a feature to a drawing

The user gives you a feature: "API rate limiting", "audit log", "bring your own
key". You have to decide what to draw before you draw anything, and this is
where an icon is won or lost — a perfectly built drawing of the wrong thing is
still the wrong icon.

**Contents** — 1 Say what it does · 2 Look for it in Phosphor · 3 Choose the
picture · 4 Compose it · 5 What Phosphor never does · 6 Worked examples

---

## 1. Say what it does

Write one plain sentence: *"Rate limiting caps how many requests a client may
make in a period."* Then underline the nouns and the verb. The icon will be
built from those: a thing (requests, a gauge, a clock) and what happens to it
(capped, blocked, slowed).

If the sentence needs "and", the feature is two ideas. Draw the one the user
would name first.

## 2. Look for it in Phosphor

```bash
python3 scripts/iconkit.py find rate limit throttle quota
```

Search with several words for the same idea — the tool knows common product
vocabulary but only matches names. Then look at the best candidates:

```bash
python3 scripts/iconkit.py sheet gauge speedometer hourglass timer prohibit -o /tmp/refs.png
```

Three things can come of this, and each is useful:

- **Phosphor already has it.** Say so in one line when you deliver — the user
  may not have found it — and still draw what they asked for unless the match
  is exact.
- **Phosphor has the parts.** A gauge, a lock, a clock. These are your
  vocabulary: the new icon should be built from the same objects, drawn the
  same way, so it reads as a sibling.
- **Phosphor has relatives.** Icons for neighbouring ideas. Your icon will sit
  beside these in a menu; pass them to `--near` so the preview lines them up.

## 3. Choose the picture

Go down this list and stop at the first that works.

1. **A physical object people already associate with the idea.** Settings is a
   gear, search is a lens, security is a shield or a lock, speed is a gauge,
   time is a clock or hourglass, storage is a cylinder. Do not get clever when
   a convention exists; conventions are why icons work without labels.
2. **An existing object plus one modifier.** This is how Phosphor builds most
   of its set, and how most product features are best drawn: `file-lock`,
   `cloud-arrow-up`, `user-gear`, `database` + `clock`, `key` + `plus`. The
   object says *what*, the modifier says *what happens to it*.
3. **A diagram of the relationship.** Branching, merging, layering, flow,
   hierarchy, a set with one member picked out: nodes and connectors, stacked
   planes, arrows. `git-branch`, `tree-structure`, `stack`, `funnel`,
   `flow-arrow`.
4. **A piece of interface.** A toggle, a slider, a cursor, a window, brackets,
   a prompt. Right when the feature *is* a UI concept (feature flags → toggle).

Modifiers and what they say:

| Modifier | Reads as | Drawn |
|---|---|---|
| plus | add, create, new | SPEC §6 |
| check | done, approved, verified, valid | SPEC §6 |
| x | remove, failed, reject | SPEC §6 |
| minus | remove one, collapse | SPEC §6 |
| arrow up / down / right | upload, download, send, export | SPEC §6 |
| arrows in a circle | sync, refresh, retry | `arrows-clockwise` |
| lock / key | restricted, secret, permission | `lock`, `key` examples |
| gear | configure | `gear` example |
| clock | scheduled, history, expiring | `clock` example |
| lightning | automatic, instant, triggered | `lightning` example |
| sparkle | AI, generated, magic | `sparkle` example |
| slash | off, disabled, hidden | SPEC §8 |
| dot / dots | status, pending, more | SPEC §3 |
| magnifier | inspect, search within | `magnifying-glass` example |
| eye | visible, preview, watch | `eye` example |

When two pictures both work, sketch both — a regular weight takes a minute —
put them on one sheet with `iconkit.py sheet a.source.svg b.source.svg -o …`,
and keep the one that is recognisable at 16 px. If they are equally good, keep
the one with fewer elements.

## 4. Compose it

- **One subject, drawn large.** It fills the 32..224 box. Everything else is
  smaller and subordinate.
- **Front on, flat.** No perspective, no three-quarter views. The single
  exception Phosphor allows itself is the isometric box (`cube`, `package`).
- **Symmetrical if the object is.** Centre it on x=128. Asymmetry is for
  objects that have a direction: a key, a magnifier, a megaphone.
- **Built from the keyline shapes** — circle r=96, square 176, rectangles — and
  from the bodies in `assets/examples/`. Start from the nearest example file
  and change it; do not start from an empty canvas when a relative exists.
- **Two to six elements.** Draw the version with everything you think it
  needs, then delete elements until removing one more would lose the meaning.
- **Leave air.** Parts that do not touch are 32 apart or more. Phosphor icons
  are airy; crowding is the most common way a new icon fails to match.

## 5. What Phosphor never does

Checking these keeps a new icon from looking like it came from another set.

- Sharp line ends or mitred corners. Everything is round.
- Mixed line weights inside one icon, or hairline detail.
- Solid black areas in the stroke weights, other than dots.
- Shading, gradients, hatching, drop shadows, highlights (the one quarter-arc
  glint on `lightbulb` is a drawn stroke, not an effect).
- Perspective and overlapping layers with hidden lines.
- Letters and words. A few glyphs exist (`text-aa`, file-type badges); do not
  spell the feature's name.
- Tiny repeated texture: rows of little teeth, grids of dots finer than 32.
- Elements that almost touch. They either join exactly or stand 32 apart.

## 6. Worked examples

**"API rate limiting"** — caps requests over time. `find rate limit throttle`
→ `gauge`, `speedometer`, `hourglass`, `prohibit`. A gauge already means
"how fast"; rate limiting is *a gauge with a ceiling*. Draw: `gauge` body, its
needle, and a short stop mark the needle rests against. Three elements.
Name: `gauge-limit`. Mention that `gauge` exists if they want stock.

**"Audit log"** — a record of who did what. Parts: `list`, `clipboard-text`,
`scroll`, `magnifying-glass`, `clock-counter-clockwise`. The record is the
subject; being *inspected* is the modifier. Draw: a document with two text
lines and a small lens over its lower-right corner. Name: `file-magnifying-glass`
— check first; Phosphor has that one. If it does, say so and stop.

**"Feature flags"** — turning features on per audience. `flag` is the literal
word and `toggle-right` is the literal mechanism. A flag alone says "report"
or "milestone" in most products; a toggle alone says "setting". Draw: a flag
whose pennant holds a small toggle knob, or a toggle with a small flag
modifier. Sketch both, compare at 16 px.

**"Bring your own key"** — customer-supplied encryption key. Parts: `key`,
`user`, `arrow-up`. Draw: `key` large, with a 48-wide arrow modifier pointing
in. Name: `key-arrow-in`.

**"Semantic search"** — search by meaning. Parts: `magnifying-glass`,
`sparkle`, `brain`. Draw: the lens with a small four-point sparkle inside it
in place of `magnifying-glass-plus`'s plus. Name: `magnifying-glass-sparkle`.
