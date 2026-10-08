---
name: iconkit
description: Design new icons in the Phosphor Icons style and build them in all six weights (thin, light, regular, bold, fill, duotone) as production SVGs, from nothing more than a description of the feature. Use this whenever someone needs an icon Phosphor does not have — "we can't find an icon for X", "make/design/draw an icon for our <feature>", "I need a custom icon that matches Phosphor", "add an icon to our set", "create the bold/fill/duotone versions" — and whenever a product feature, nav item, empty state or button is described and an icon is wanted for it, even if Phosphor or SVG is never mentioned. Also use it to revise an icon made this way, to check whether Phosphor already has a suitable icon, and to add finished icons to a Figma icon library as components (only after asking).
---

# IconKit

Turn a feature description into an icon that could have shipped with Phosphor:
same grid, same strokes, same six weights, same file format.

> **Draw one skeleton. Let the build make the weights. Then look at it.**

You write a single small SVG of centrelines. `scripts/iconkit.py` strokes it at
Phosphor's four widths, builds the fill and duotone you specify, expands
everything to clean outlined paths, checks it against rules measured from
Phosphor's 1,512 icons, and renders a preview that puts your icon in a row with
real ones. You never write a weight by hand, and you never have to guess
whether the result fits: the preview shows you.

This is not approximate. The 44 sources in `assets/examples/` are real Phosphor
icons rebuilt this way, and they land on the originals' outlines.

Paths in this skill are relative to the skill's own folder. Python 3.8+, no
installs.

## Workflow

1. **Say what the feature does** in one sentence, and pick out the thing and
   what happens to it. → `references/concept.md`
2. **Search Phosphor** with several words for the idea, and look at what comes
   back. You are looking for an existing answer, for parts, and for the
   neighbours your icon will sit beside.
   ```bash
   python3 scripts/iconkit.py find audit log history record
   python3 scripts/iconkit.py sheet list-checks clipboard-text scroll clock-counter-clockwise -o /tmp/refs.png
   ```
3. **Choose the picture**: a conventional object, or an object plus one
   modifier, or a small diagram. Name it the Phosphor way — what is drawn,
   object first (`file-lock`, not `secure-docs`). If it is not obvious which
   picture is best, sketch two or three and compare them on one sheet.
4. **Read `SPEC.md`** if you have not this session. It is short and it holds
   every number: the grid, the keyline shapes, the standard glyphs, the source
   format.
5. **Write the skeleton**, starting from the nearest example rather than a
   blank file. Save it as `icons/<name>/<name>.source.svg` in the user's
   project unless they say where. → `references/examples.md`
6. **Decide fill and duotone**: which body goes solid, what is knocked out of
   it, what gets the tint. → `references/weights.md`
7. **Build**, naming six related Phosphor icons to line up against:
   ```bash
   python3 scripts/iconkit.py build icons/file-clock/file-clock.source.svg --near file,file-text,clock,calendar,folder,timer
   ```
8. **Look at `preview.png`** (open the image) and judge it with the list below.
   Fix the source, rebuild, look again. Three or four rounds is normal; the
   first build is a draft.
9. **Deliver** (see below), then offer the Figma step.

## Looking at the preview

The checker catches what can be measured. Whether it is a good icon is
something only looking decides, and the preview is laid out to make each
question answerable at a glance.

**Top row — six weights, large, with the 24-unit margin drawn.**
- Is it instantly the thing you meant? Would a stranger name it?
- Is it centred and does it fill the box, the way the circle and square
  keylines do? Small and floating is the commonest fault.
- Bold: is every opening still open, every part still separate?
- Fill: is it the same icon carved from a solid — not a blob, not the outline
  again? Are the knocked-out details as clear as the regular's strokes?
- Duotone: is exactly the main mass shaded?

**Middle — real pixels at 16, 20, 24, 32, enlarged.**
- At 16 px, can you still tell what it is? Which detail has turned to mush?
  That detail is too small or too close to its neighbour: enlarge it, space
  it to 32 units, or cut it. Phosphor cuts.

**Bottom — yours, underlined, in a row of real Phosphor icons.**
- Cover the underline. Can you pick yours out as the odd one? If it looks
  smaller, lighter, darker, busier or more angular than its neighbours, that
  is the thing to fix. It should be boring in this row.

Then one last pass: is there an element you could delete without losing the
meaning? Delete it and rebuild.

## Rules that keep it Phosphor

These are the ones that matter most; `SPEC.md` has the rest.

- **Borrow before you draw.** A body copied from `assets/examples/` or from
  `iconkit.py show <name> duotone` (the tint path of any Phosphor icon is its
  body's centreline) is already right. A body drawn from memory rarely is.
- **Skeleton inside 32..224, long side filling it.** Circle `r=96`, square
  `40..216`. Whole-number coordinates on multiples of 8, or 4 for details.
- **Everything round**: caps, joins. Rectangle corners `rx="8"`. Dots are
  `<circle r="4" fill="currentColor"/>`.
- **32 units between parallel strokes; no opening under 16.** Sixteen units is
  one pixel at 16 px.
- **Two to six elements.** One subject, large; at most one modifier.
- **Knockouts come after the solid they cut** — elements paint in order.
- **Edit the source, never the output.** The six SVGs are build products; a
  hand-edit is lost on the next build and breaks the match between weights.
- **No errors at delivery.** A warning may stay if you can say why (a subject
  that really is wide; a counter Phosphor would also let close). Say it.

## Delivering

Show the preview image, then keep the note short:

- the name, and in a few words what is drawn and why it says the feature;
- where the files are (the six SVGs, the source, the preview);
- anything Phosphor already has that is close, by name, in one line;
- any warning you chose to keep, and the reason.

If their project uses `@phosphor-icons/react`, add `--react` to the build: it
writes `<Name>.tsx`, a component that takes `weight`, `size` and `color`
exactly like a built-in Phosphor icon.

When the user asks for a change ("thicker gauge", "lose the dots", "the lock
should be bottom-right"), edit the source and rebuild; do not start over.

For a set of related icons, build the shared body once and copy that element
unchanged into each source, so the family is identical where it should be.

## Figma

After delivering, ask whether they want the icon added to their Figma icon
library as components, and which file. Do nothing in Figma until they answer
both. Then follow `references/figma.md`: it reads how the file already builds
its icons — set or separate components, weight names, size, colour style — and
matches that, in a section of its own.

## The tools

```bash
python3 scripts/iconkit.py find <words…>             # search Phosphor's names by idea
python3 scripts/iconkit.py sheet <names|sources…> -o out.png   # six-weight contact sheet
python3 scripts/iconkit.py show <name> [weight]      # a real icon's path data and ink box
python3 scripts/iconkit.py build <source> [--near a,b,c,d,e,f] [--react] [-o dir]
python3 scripts/iconkit.py check <source>            # the checker alone
python3 scripts/iconkit.py compare <source> <name>   # how far a source is from a real icon
python3 scripts/selftest.py                          # after changing the scripts
```

`sheet` accepts source files as well as Phosphor names, so a draft can sit on
the same sheet as the icons it should match.

## Reference files

| File | Read it when |
|---|---|
| `SPEC.md` | Before the first skeleton of a session. Grid, sizes, source format, standard glyphs, modifiers, slash, naming. |
| `references/concept.md` | Choosing what to draw for a feature. |
| `references/examples.md` | Finding a body or a pattern to start from. |
| `references/weights.md` | Deciding fill, duotone and bold; diagnosing a bad preview. |
| `references/figma.md` | The user has said yes to Figma. |
