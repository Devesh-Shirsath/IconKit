#!/usr/bin/env python3
"""Prove the pipeline still works. Run after changing anything in scripts/.

Two independent checks over every source in assets/examples/:

  1. Engine: the outlined path must cover exactly the points the skeleton says
     are painted (thousands of probe points per weight, tested both ways).
  2. Fidelity: each example is a real Phosphor icon rebuilt from a skeleton, so
     its thin, light and regular weights must land on the real outlines.
     Fill and duotone must too, except where the example is marked approximate.

    python3 scripts/selftest.py
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import iconkit as ik   # noqa: E402
import outline as ol   # noqa: E402
import svgpath as sp   # noqa: E402

# Examples whose fill or duotone is a simplification of Phosphor's hand-tuned version.
APPROXIMATE = {"house": ("fill",), "cloud": ("fill",), "cloud-arrow-up": ("fill",), "globe": ("fill",),
               "key": ("fill",), "magnifying-glass": ("duotone",),
               # data-gap cuts the base flat where Phosphor trims and re-caps it by hand
               "bell-slash": ("thin", "light", "regular", "fill", "duotone")}
STROKE_LIMIT = 1.5    # % of ink; Phosphor's own 2-decimal rounding accounts for about 1%
DESIGN_LIMIT = 1.0


def _inside(polys, x, y):
    wn = 0
    for pts in polys:
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            if (y0 <= y) != (y1 <= y):
                if x0 + (y - y0) * (x1 - x0) / (y1 - y0) > x:
                    wn += 1 if y1 > y0 else -1
    return wn != 0


def engine_errors(icon, probes=1500):
    """Count probe points where the outline and the skeleton disagree."""
    bad = 0
    seed = 12345
    for w in ik.WEIGHTS:
        ops, tint = ik.layers(icon, w)
        for layer in (ops, tint):
            if not layer:
                continue
            subs = ol.outline(layer, icon.soft)
            polys = sp.flatten(subs, 0.005)
            edges = [s for op in layer for s in op._segs]
            for _ in range(probes):
                seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
                x = 256.0 * seed / 0x7FFFFFFF
                seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
                y = 256.0 * seed / 0x7FFFFFFF
                want = ol.painted(layer, x, y)
                if want == _inside(polys, x, y):
                    continue
                # disagreement is only real if the point is clear of every edge
                near = False
                for op in layer:
                    for s in op._segs:
                        d = ol._dist_seg(s, x, y)
                        if abs(d - op.hw) < 0.12 or (op.filled and d < 0.12):
                            near = True
                            break
                    if near:
                        break
                if not near:
                    bad += 1
    return bad


def main():
    sources = sorted(glob.glob(os.path.join(ik.ASSETS, "examples", "*.svg")))
    failures = 0
    print("%-24s %-7s %s" % ("example", "engine", "difference from real Phosphor, % of ink"))
    for path in sources:
        name = os.path.basename(path)[:-4]
        icon = ik.load(path)
        built = ik.build(icon)
        errs = engine_errors(icon)
        cells = []
        ok = errs == 0 and not any(lvl == "error" for lvl, _ in icon.notes)
        for w in ik.WEIGHTS:
            d = ik._coverage(built[w], ik.phosphor_parts(name, w))
            approx = w in APPROXIMATE.get(name, ()) or w == "bold"
            limit = STROKE_LIMIT if w in ("thin", "light", "regular") else DESIGN_LIMIT
            flag = ""
            if not approx and d > limit:
                ok = False
                flag = "!"
            cells.append("%s %.2f%s%s" % (w[:3], d, "~" if approx else "", flag))
        if not ok:
            failures += 1
        print("%-24s %-7s %s" % (name, "ok" if errs == 0 else "%d BAD" % errs, "  ".join(cells)))
    print("\n%d examples, %d failing.  (~ = Phosphor hand-tunes this weight; not expected to match)"
          % (len(sources), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
