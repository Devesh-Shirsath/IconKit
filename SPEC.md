# IconKit spec

Every number here was measured from the 1,512 icons × 6 weights of Phosphor 2.1,
or is a rule of the source format that `scripts/iconkit.py` builds from. Nothing
is a matter of taste. If you need a value that is not here, reuse the nearest
one that is.

**Contents** — 1 Canvas and weights · 2 Size and position · 3 Strokes, corners,
dots · 4 Spacing and small sizes · 5 The source format · 6 Standard parts ·
7 Modifiers and badges · 8 The slash · 9 Naming · 10 What the checker enforces

---

## 1. Canvas and weights

The canvas is `0 0 256 256`. An icon is drawn **once, as a skeleton of
centrelines**. The four stroke weights are that same skeleton stroked at four
widths — Phosphor does not redraw between thin and bold, and neither do you.

| Weight  | Stroke | Visible dot radius | At 16 px | At 24 px | At 32 px |
|---------|--------|--------------------|----------|----------|----------|
| thin    | 8      | 8                  | 0.5 px   | 0.75 px  | 1 px     |
| light   | 12     | 10                 | 0.75 px  | 1.125 px | 1.5 px   |
| regular | 16     | 12                 | 1 px     | 1.5 px   | 2 px     |
| bold    | 24     | 16                 | 1.5 px   | 2.25 px  | 3 px     |
| fill    | 16, bodies solid | 12       |          |          |          |
| duotone | 16, plus a 20% tint layer | 12 |        |          |          |

Measured over every side of every icon's ink box: against regular, thin is 4
units smaller and light 2 smaller in over 99% of cases; bold is 4 larger in
92% (the rest are bold's hand adjustments, `references/weights.md` §8). The
centreline does not move.

One unit is 1/16 of a pixel at 16 px. **16 units is one pixel at the smallest
size the icon will be used.** That single fact explains most of the rules below.

## 2. Size and position

Think in skeleton coordinates; the ink is 8 units wider on each side at regular.

| Keyline shape      | Skeleton                                   | Ink at regular        |
|--------------------|--------------------------------------------|-----------------------|
| Circle             | `cx=128 cy=128 r=96`                       | 24..232               |
| Square             | `x=40 y=40 width=176 height=176 rx=8`      | 32..224               |
| Landscape rectangle| `x=32 y=48 width=192 height=160 rx=8`      | 24..232 × 40..216     |
| Portrait (a file)  | 48..208 × 32..224                          | 40..216 × 24..232     |
| Pill (a toggle)    | `x=16 y=64 width=224 height=128 rx=64`     | 8..248 × 56..200      |
| Full-size glyph    | lines run 40..216; diagonals 56..200       | 32..224               |

A square is drawn smaller than a circle on purpose: it has more area for the
same width, so matching boxes would make it look bigger.

Measured from Phosphor's regular weight:

- **Long side of the ink**: 208 is the most common (30%), then 224, 192, 240.
  Only 5% of icons are under 176. If your icon's long side is under 176 it will
  look small next to its neighbours.
- **Where the ink starts**: 24 units from the edge (29% of icons), 32 (20%),
  16 (15%), 40 (12%), 8 (10%). Aim the skeleton at **32..224**. Go out to 24..232
  for a subject that is long in one direction. Past that is rare.
- **Centring**: 75% of icons are centred exactly left-to-right and 58%
  top-to-bottom; 95% are within 12 units on either axis. Centre the ink box on
  (128, 128) unless the subject's visual weight clearly sits elsewhere (a
  magnifying glass leans up-left because its handle hangs down-right).
- **Ink coverage** at regular: 10–27% of the canvas (middle 90%), median 19.5%.
  Bold's median is 29%, fill's 38%. Far below the range reads as wispy; far
  above reads as heavy or busy.

## 3. Strokes, corners, dots

- **Caps and joins are always round.** No butt caps, no mitres, no exceptions.
- **Corner radius 8** on the centreline of rectangles and boxes. At regular that
  makes the outside corner radius 16 and the inside corner square. Use larger
  radii only when the object itself is soft: 16, 24 (a robot's head), or a full
  pill. Polygons (triangles, diamonds, lightning) have sharp skeleton corners;
  the round join does the softening.
- **Dots** are filled circles with skeleton radius 4: `<circle r="4"
  fill="currentColor"/>`. The stroke grows them to 8 / 10 / 12 / 16 across the
  weights, which is exactly Phosphor's series. Never draw a dot as a short line.
- **Coordinates are whole numbers**, on multiples of 8 where you can and 4 for
  small details. The exceptions are points that follow from geometry: where a
  diagonal meets a circle, where a tangent lands.
- **Angles**: horizontal, vertical and 45° first. Phosphor's check, x, carets
  and arrowheads are all 45°. Other angles appear when a shape demands them
  (a funnel, a lightning bolt) and should be used once, not mixed.
- **Curves**: circles and circular arcs first. Use béziers for the few shapes
  that are not arcs (a bell's flare, a heart, a shield's point).

## 4. Spacing and small sizes

- **Parallel strokes sit 32 or more apart**, centre to centre. At 32 the gap is
  16 at regular (one pixel at 16 px) and 8 at bold. Text lines in `file-text`
  are 32 apart; the bars of `list` are 64 apart.
- **No opening narrower than 16 units at regular.** Measured: in 99% of
  Phosphor's icons the narrowest opening is 16 or wider. In bold, 99% keep 12
  or wider and 95% keep 16.
- **Knocked-out details in the fill weight** are full 16-unit lines and
  12-radius dots. Anything finer disappears into the solid.
- **Element budget**: most icons need 2–6 elements. If you are past 9, you are
  drawing an illustration.

## 5. The source format

A source is an ordinary SVG that renders as the regular weight in any viewer.
Save it as `<name>.source.svg`. The root is always:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="none"
     stroke="currentColor" stroke-width="16" stroke-linecap="round" stroke-linejoin="round">
  …
</svg>
```

**Shapes**: `line`, `polyline`, `polygon`, `circle`, `ellipse`, `rect` (with
`rx`), `path` (every command), grouped with `<g>`, reused with `<use href="#id">`.
`transform` works on any of them and moves geometry only — a scaled-down copy
keeps the full stroke width, which is what you want for a smaller glyph.

**How an element paints**

| You write | It paints |
|---|---|
| nothing extra | a stroke, at the weight being built |
| `fill="currentColor"` | fill **and** stroke, in every weight (how dots are made) |
| `fill="currentColor" stroke="none"` | fill only, no growth with weight |

**Roles** — attributes that say what an element becomes in a designed weight.
They are inherited from a `<g>`.

| Attribute | Value | Meaning |
|---|---|---|
| `data-fill` | `solid` | In the fill weight: filled as well as stroked. Use on the main body. |
| | `knockout` | In the fill weight: whatever this element paints is *removed* instead (a white line or dot cut into a solid). |
| | `hole` | In the fill weight: the shape's interior, measured at the centreline, is removed. No stroke. (An eye's pupil, a gear's centre.) |
| | `plate` | Exists **only** in the fill weight, as a solid. The container an open glyph is knocked out of. |
| | `none` | Left out of the fill weight. |
| `data-duotone` | `tint` | In duotone: stroked as usual, and its interior joins the 20% layer. |
| | `plate` | Exists **only** in duotone, as tint with no stroke. The backing shape for an open glyph. |
| | `none` | Left out of duotone. |
| `data-only` | weights | Exists only in the listed weights, e.g. `data-only="fill duotone"`. |
| `data-not` | weights | Left out of the listed weights, e.g. `data-not="bold"`. |
| `data-erase` | units | Before painting, clears a halo this wide around itself. For a part that must sit on top of another with clear air around it. |
| `data-gap` | units | On a straight line: clears a strip on one side of it. The slash recipe (§8). |
| `data-paint` | `knockout` | Removes paint in every weight. Rarely needed. |

An element can be a plate in both: `data-fill="plate" data-duotone="plate"`.

**Elements paint in document order; later ones cover earlier ones.** A knockout
must come *after* the solid it cuts. To put something back on top of a cut,
draw it again afterwards (see `examples/globe.svg`, which redraws the rim).

**Alternates.** When one weight needs different geometry, write both and gate
them:

```svg
<polyline points="144 56 216 128 144 200" data-not="fill duotone"/>
<polygon  points="144 56 216 128 144 200" data-only="fill duotone" data-fill="solid" data-duotone="tint"/>
```

**What the build writes** — six files in Phosphor's own format and naming
(`name.svg` is regular, then `name-thin.svg`, `-light`, `-bold`, `-fill`,
`-duotone`), each a single outlined path with `fill="currentColor"`, duotone
with its tint path at `opacity="0.2"` first; plus `preview.png`, and with
`--react` a `Name.tsx` for `@phosphor-icons/react`.

## 6. Standard parts

Skeleton coordinates of glyphs Phosphor draws the same way every time. Use them
as written; do not re-derive.

| Part | Full size | Inside a circle (r=96) or square |
|---|---|---|
| plus | `40,128→216,128` and `128,40→128,216` | `88,128→168,128` and `128,88→128,168` (80 wide) |
| minus | `40,128→216,128` | `88,128→168,128` |
| x | `56,56→200,200` and `200,56→56,200` | `96,96→160,160` and `160,96→96,160` (64 wide) |
| check | polyline `40,144 96,200 224,72` | polyline `88,136 112,160 168,104` |
| arrow → | line `40,128→216,128`, head `144,56 216,128 144,200` | line `88,128→168,128`, head `136,96 168,128 136,160` |
| caret › | polyline `96,48 176,128 96,208` | |
| arrow ↗ | line `64,192→192,64`, head `88,64 192,64 192,168` | |
| ! | | line `128,80→128,136`, dot at `128,172` |
| three dots | dots at `60,128` `128,128` `196,128` | dots at `84,128` `128,128` `172,128` |
| clock hands | | polyline `128,72 128,128 184,128` |

Arrowhead arms reach 72 back from the tip at full size and 32 when small. A
check's short arm is a little under half its long arm.

Bodies you will reuse are in `assets/examples/` as tested sources — user,
file, folder, shield, bell, cloud, chat bubble, gear, lock, database, cube
faces, tag, eye, heart, house, calendar, robot, cpu, key, funnel, stack, globe.
See `references/examples.md`. For any other Phosphor icon,
`iconkit.py show <name> duotone` prints its tint path, **which is the
centreline of its main body** and can be pasted into a source as a `<path>`.

## 7. Modifiers and badges

Phosphor makes families by adding a small glyph to a base object, and it avoids
overlap: the modifier goes where there is room, and the base makes room.

- **Inside the body**, when the body is a container (file, folder, cloud,
  shield, calendar, magnifier lens): 48 wide in a narrow body (`file-plus`:
  plus centred on 128,152), 64 in a lens, 80 in a full circle or square.
  Centre it on the body's visual centre, not the canvas.
- **Beside the body**, when the body is a figure (user): shift and shrink the
  base — `user-plus` moves the head to `cx=108 cy=100 r=60` and the shoulders
  to span 24..192 — and put a 48-wide modifier centred near (224, 136).
- **A second object** (a small lock on a file): give it a corner, usually
  bottom-left or bottom-right, and stop the base's outline short of it rather
  than drawing over it.
- **Motion and emphasis** (ringing, sparkle): short strokes outside the body,
  at least 24 from it.

Use `data-erase` only when a part truly has to overlap; a 12–16 unit halo is
enough. If you find yourself reaching for it, first ask whether the modifier
could simply go inside or beside.

## 8. The slash

Every `-slash` icon in Phosphor uses the same line: `48,40 → 208,216`. The base
drawing continues right up to the slash on its lower-left side and is held back
32 skeleton units on its upper-right side. Write the base as normal, then:

```svg
<line x1="48" y1="40" x2="208" y2="216" data-gap="32"/>
```

`data-gap` clears that strip in every weight, including the solid body in fill.
The duotone tint is deliberately left whole, as Phosphor leaves it. A negative
value clears the other side.

## 9. Naming

Kebab-case, the object first, then what modifies it: `file-lock`,
`cloud-arrow-up`, `user-circle-plus`. Name what is *drawn*, not the feature it
stands for — `gauge-lock`, not `rate-limiting` — because that is how every
other icon in the set is found. Say which feature it is for in your note to the
user. If the user gives a name, use theirs. Do not reuse an existing Phosphor
name.

## 10. What the checker enforces

`iconkit.py build` and `check` report three levels.

**error** — fix before delivering: bold leaves the canvas · the fill weight has
nothing solid · duotone has no tint · a knockout is painted over by a later
solid · a weight is empty · the viewBox is wrong.

**warn** — fix unless you can say why not: ink past 8..248 · long side under
176 · more than 12 off centre · an opening under 16 (regular, fill) or 12
(bold) · a counter that closes or parts that merge in bold · more than 9
elements · a name that collides with Phosphor's.

**note** — information: ink past 16..240 · ink coverage outside 10–27% · fill
barely heavier than regular · many off-grid coordinates.

A clean check means the icon obeys the measurable rules. It does not mean the
icon is good. Only looking at `preview.png` tells you that.
