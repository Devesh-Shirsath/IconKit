# Designing fill, duotone and bold

Thin, light and regular come free from the skeleton. Fill and duotone are
*designed* — Phosphor decides, icon by icon, what turns solid and what gets the
tint — and bold sometimes needs a nudge. This file is how to make those
decisions the way Phosphor makes them. Every pattern names an example in
`assets/examples/` that reproduces a real Phosphor icon with it.

**Contents** — 1 Find your pattern · 2 Closed body · 3 Body with detail ·
4 Open glyph · 5 Several bodies · 6 Body plus stroke parts · 7 Two kinds of
hole · 8 Bold · 9 Mistakes that show up in the preview

---

## 1. Find your pattern

Look at the regular weight and ask what the ink encloses.

| The icon is… | Fill | Duotone | Section |
|---|---|---|---|
| one closed shape | all solid | tint the shape | 2 |
| a closed shape with marks inside | solid, marks knocked out | tint the shape | 3 |
| lines only, nothing enclosed | solid plate, glyph knocked out smaller | plate behind the glyph | 4 |
| several closed shapes | all solid, or only the one that matters | tint the same ones | 5 |
| a body with lines sticking out | body solid, lines stay lines | tint the body | 6 |

The test for both weights is the same: **squint at regular, then at yours.
The same icon, the same size, the same parts in the same places** — fill is
that icon carved from a solid, duotone is that icon with its main mass shaded.

## 2. One closed body

Mark it once; it does both jobs.

```svg
<path d="…shield…" data-fill="solid" data-duotone="tint"/>
```

`solid` fills the shape *and* keeps its stroke, so the silhouette is exactly
regular's outer edge. (Measured: in 84% of Phosphor's icons the fill weight
occupies the identical ink box to regular.) Examples: `shield`, `heart`, `chat`, `funnel`, `lightning`, `cloud`.

## 3. A body with detail inside

The body goes solid; what was drawn inside it is cut out as white lines and
dots at regular thickness.

```svg
<circle cx="128" cy="128" r="96" data-fill="solid" data-duotone="tint"/>
<polyline points="128 72 128 128 184 128" data-fill="knockout"/>
```

Order matters: the knockout comes after the solid. Examples: `clock`,
`check-circle`, `shield-check`, `warning` (a line and a dot), `lock`, `tag`,
`trash`, `file-text`.

A knockout is the element's own paint removed — a 16-unit line, a 12-radius
dot. If the detail is a closed shape whose *inside* should be empty, that is a
hole (§7).

## 4. An open glyph

Nothing is enclosed, so there is nothing to fill. Phosphor gives the glyph a
container: a rounded square or rectangle that goes solid, with the glyph
redrawn smaller inside it and knocked out. In duotone, the full-size glyph
keeps its lines and gets a quiet backing shape.

```svg
<g data-not="fill">                      <!-- the glyph, in five weights -->
  <line x1="40" y1="128" x2="216" y2="128"/>
  <line x1="128" y1="40" x2="128" y2="216"/>
</g>
<rect x="40" y="40" width="176" height="176" rx="8" data-fill="plate"/>
<g data-only="fill" data-fill="knockout"> <!-- the same glyph, smaller, cut out -->
  <line x1="72" y1="128" x2="184" y2="128"/>
  <line x1="128" y1="72" x2="128" y2="184"/>
</g>
<rect x="40" y="40" width="176" height="176" rx="16" data-duotone="plate"/>
```

- **Fill plate**: the square `40,40 176×176 rx=8`, or for a wide glyph the
  rectangle `32,48 192×160 rx=8`. A circle `r=96` for a round subject.
- **The knocked-out glyph** leaves at least 32 units of solid between itself
  and the plate's edge. In practice it is the full-size glyph at about 64% —
  plus goes from 176 wide to 112, the bars of `list` from 176 to 128 — redrawn
  on the grid, not scaled blindly.
- **Duotone plate**: the same footprint with `rx=16`, or a shape that hugs the
  glyph (`code` uses a flat hexagon between its brackets, `list` a plain
  rectangle from the first bar to the last).

Examples: `plus`, `list`, `code`, `terminal`.

An arrow is the exception: it is open, but its head is nearly a triangle, so
Phosphor closes the head and fills that instead of using a plate. See
`arrow-right`, which also shortens the shaft so it stops at the head.

## 5. Several closed shapes

If the shapes are equals — the three boxes of `tree-structure`, the bars of
`chart-bar` — make them all solid and tint them all.

If one is the subject and the rest are context, only the subject goes solid
and gets the tint; the others stay outlined. That keeps the hierarchy the
regular weight had. `git-branch` fills one node of three. `database` fills the
top disc and leaves the sides as lines. `stack` fills the top layer.
`envelope` fills only the flap; `file` and `folder` tint only the fold and the
tab.

When in doubt, tint less. A duotone icon with everything shaded has no
second tone.

## 6. A body with strokes sticking out

Handles, antennae, legs, connectors, rings around the body: leave them as
strokes in every weight. Only mark the body.

```svg
<path d="M88,88V56a40,40,0,0,1,80,0V88"/>                     <!-- shackle: always a stroke -->
<rect x="40" y="88" width="176" height="128" rx="8" data-fill="solid" data-duotone="tint"/>
```

Examples: `lock`, `bell` (the clapper), `robot` (the antenna), `cpu` (the
pins), `magnifying-glass` (the handle), `user-plus` (the plus).

A figure's shoulders are an open arc in regular. For fill, close it:

```svg
<path d="M32,216c19.37-33.47,54.55-56,96-56s76.63,22.53,96,56"  data-not="fill"/>
<path d="M32,216c19.37-33.47,54.55-56,96-56s76.63,22.53,96,56Z" data-only="fill" data-fill="solid"/>
```

## 7. Two kinds of hole

Phosphor cuts closed details out of a solid in two sizes, and the difference
is visible.

**The interior only** — `data-fill="hole"`. The white area is the shape at its
centreline. Use it when the detail is a ring whose outer edge should survive
as part of the solid: an eye's pupil, a gear's centre.

```svg
<circle cx="128" cy="128" r="40" data-fill="hole"/>           <!-- white disc, radius 40 -->
```

**The whole silhouette** — a filled alternate, knocked out. The white area
includes the stroke, so it is 8 units bigger all round. Use it when the detail
is an object sitting on the solid: a toggle's knob.

```svg
<circle cx="80" cy="128" r="32" data-not="fill" data-duotone="tint"/>
<circle cx="80" cy="128" r="32" fill="currentColor" data-only="fill" data-fill="knockout"/>  <!-- white disc, radius 40 -->
```

To leave a solid shape *inside* a hole, paint it afterwards (`cpu`: hole, then
a filled square on top).

A tint can have a hole too: give a `data-duotone="plate"` path two subpaths and
`fill-rule="evenodd"` (`eye`, `gear`, `cpu`).

## 8. Bold

Build it, then look. Bold adds 4 units to every side of every stroke, so the
places to check are wherever two strokes face each other across a small gap.
The checker reports openings under 12 and counters that close. Expect to
adjust: Phosphor itself hand-tunes bold in roughly a third of its icons.

Phosphor's fixes, in the order to try them:

1. **Move the detail 4–8 units away from the wall it is crowding.** `tag`'s dot
   moves from (84, 84) to (88, 88). `file`'s fold moves inward.
2. **Shrink an inner shape by 8** so its outer edge stays where it was. `eye`'s
   pupil goes from r=40 to r=32.
3. **Simplify.** `robot`'s mouth dividers shrink to short ticks.

Write the fix as an alternate — the original with `data-not="bold"`, the
adjusted copy with `data-only="bold"` — and leave the other weights alone.

If bold needs more than two alternates, the regular drawing is too tight.
Open it up at the source; an icon that only works at one weight is not
finished.

## 9. Mistakes that show up in the preview

| What you see | What happened | Fix |
|---|---|---|
| Fill looks identical to regular | nothing is marked `solid` or `plate` | §1 |
| Fill is a black blob with no detail | details are not marked `knockout`, or come before the solid | reorder; the checker flags this |
| White detail in fill is hair-thin at 16 px | knocked out a shape's *interior* that is too small, or two knockouts are closer than 32 | enlarge to full-size lines and dots; drop detail |
| Fill's silhouette is bigger or smaller than regular's | the solid is a different shape from the regular body | make the solid the same element as the body |
| Duotone tint spills outside the outline | the tinted element is an open path whose closing line cuts across | add a closed `data-duotone="plate"` path instead |
| Duotone is grey everywhere | every element is tinted | §5: tint the subject only |
| Bold has a dark knot | strokes under 32 apart | §8 |
| Thin looks spindly and empty | the icon relies on stroke thickness for its mass | enlarge the shapes; add nothing |
