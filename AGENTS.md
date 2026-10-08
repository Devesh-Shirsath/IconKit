# IconKit — notes for AI agents

This repository is an icon-design skill: it turns a feature description into a
new icon in the Phosphor style, built in all six weights from one skeleton.

## To make an icon

1. Read **`SKILL.md`** for the workflow, then **`SPEC.md`**. The spec is
   self-contained — the grid, the stroke widths, the source format, the
   standard parts, what the checker enforces.
2. **Search before drawing.** `python3 scripts/iconkit.py find <words…>` — the
   icon, or most of it, may already exist in Phosphor.
3. **Borrow before you draw.** Start from the nearest file in
   `assets/examples/`, or paste a real body from
   `python3 scripts/iconkit.py show <name> duotone`. A body drawn from memory
   is rarely right.
4. Write **one** `<name>.source.svg`. Never write a weight by hand, and never
   edit the built SVGs — they are build products.
5. Build, then open `preview.png` and look at it before answering:
   `python3 scripts/iconkit.py build <source> --near a,b,c,d,e,f`
6. Write SVG code. Never use an image-generation model for this.

## Don't read these — large, and not needed to draw

- `assets/phosphor.json.gz` — a binary index of every Phosphor path. Query it
  through `iconkit.py find`, `show` and `sheet` instead.
- `showcase/` — finished output, there for people reading the README.
- `scripts/outline.py`, `scripts/raster.py`, `scripts/svgpath.py` — the
  geometry engine. You call it through `iconkit.py`.

## Reading from a link, without cloning

Fetch the raw files, not the GitHub pages around them:

- https://raw.githubusercontent.com/Devesh-Shirsath/IconKit/main/SKILL.md
- https://raw.githubusercontent.com/Devesh-Shirsath/IconKit/main/SPEC.md
- https://raw.githubusercontent.com/Devesh-Shirsath/IconKit/main/references/weights.md

Reading is enough to write a skeleton. Building the six weights needs the
scripts, so clone the repository for that. Python 3.8+, standard library only.

## Changing the skill itself

`scripts/iconkit.py` is the source of truth for every number in `SPEC.md`.
After changing anything in `scripts/`:

```bash
python3 scripts/selftest.py
```

It rebuilds the 44 sources in `assets/examples/` and compares each weight with
the real Phosphor icon. All 44 must pass.
