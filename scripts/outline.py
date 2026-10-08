"""Turn painted stroke skeletons into one clean outlined path.

Phosphor ships its icons flattened: every stroke expanded to a filled shape and
everything unioned into a single path. This module does the same job without
any dependencies, and does it exactly rather than approximately:

  1. every curve in the skeleton is reduced to straight lines and circular arcs
     (cubic beziers are fitted with biarcs to within `tol` units);
  2. the offset of a line is a line and the offset of an arc is an arc, so every
     possible piece of the final outline is known in closed form;
  3. those candidate pieces are cut where they cross each other, and each piece
     is kept only if the painted region lies on exactly one side of it;
  4. the survivors are chained into closed loops.

Step 3 asks "is this point painted?" directly of the skeleton (distance to a
stroke, winding of a fill), so tangencies and coincident edges - which is most
of what a round-capped, round-joined icon is made of - cannot confuse it.

A layer is a list of paint operations applied in order, like paint on paper:

    Op(subpaths, half_width, filled, erase)

`erase=True` removes paint laid down by earlier operations.

Standard library only.
"""
import math

from svgpath import TAU, seg_start, seg_end, cubic_point

SNAP = 1e-6       # points closer than this are the same point
PROBE = 1e-4      # how far off a piece we look to see which side is painted
GRAZE = 4e-4      # curves that overlap by less than this only touch; must exceed PROBE,
                  # so that every sliver we do cut out is thick enough to be probed


class Op(object):
    __slots__ = ("subpaths", "hw", "filled", "erase", "evenodd", "_segs", "_box")

    def __init__(self, subpaths, hw=0.0, filled=False, erase=False, evenodd=False):
        self.subpaths = subpaths
        self.hw = float(hw)
        self.filled = filled
        self.erase = erase
        self.evenodd = evenodd
        self._segs = [s for segs, _ in subpaths for s in segs]
        xs, ys = [], []
        for s in self._segs:
            if s[0] == "L":
                xs += [s[1], s[3]]
                ys += [s[2], s[4]]
            else:
                xs += [s[1] - s[3], s[1] + s[3]]
                ys += [s[2] - s[3], s[2] + s[3]]
        pad = self.hw + 2 * PROBE
        self._box = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad) if xs else None

    def contains(self, x, y):
        b = self._box
        if b is None or x < b[0] or x > b[2] or y < b[1] or y > b[3]:
            return False
        if self.hw > 0:
            hw = self.hw
            for s in self._segs:
                if _dist_seg(s, x, y) < hw:
                    return True
        if self.filled:
            wn = 0
            for segs, closed in self.subpaths:
                wn += _winding(segs, x, y)
            return (wn & 1) == 1 if self.evenodd else wn != 0
        return False


def painted(ops, x, y):
    inside = False
    for op in ops:
        if op.contains(x, y):
            inside = not op.erase
    return inside


# ---------------------------------------------------------------- measuring

def _in_span(a0, da, ang, slack=0.0):
    """Offset of `ang` along an arc starting at a0 with signed sweep da, or None."""
    d = (ang - a0) if da > 0 else (a0 - ang)
    d %= TAU
    span = abs(da)
    if d <= span + slack:
        return d
    if TAU - d <= slack:
        return 0.0
    return None


def _dist_seg(s, x, y):
    if s[0] == "L":
        _, x0, y0, x1, y1 = s
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        t = ((x - x0) * dx + (y - y0) * dy) / L2 if L2 else 0.0
        t = 0.0 if t < 0 else (1.0 if t > 1 else t)
        return math.hypot(x - (x0 + t * dx), y - (y0 + t * dy))
    _, cx, cy, r, a0, da = s
    ang = math.atan2(y - cy, x - cx)
    if abs(da) >= TAU - 1e-12 or _in_span(a0, da, ang) is not None:
        return abs(math.hypot(x - cx, y - cy) - r)
    a1 = a0 + da
    return min(math.hypot(x - (cx + r * math.cos(a0)), y - (cy + r * math.sin(a0))),
               math.hypot(x - (cx + r * math.cos(a1)), y - (cy + r * math.sin(a1))))


def _winding(segs, px, py):
    """Signed crossings of the ray going +x from (px, py); open subpaths are closed implicitly."""
    wn = 0
    if not segs:
        return 0
    sx, sy = seg_start(segs[0])
    ex, ey = seg_end(segs[-1])
    lines = []
    if abs(sx - ex) > 1e-9 or abs(sy - ey) > 1e-9:
        lines.append((ex, ey, sx, sy))
    for s in segs:
        if s[0] == "L":
            lines.append(s[1:])
            continue
        _, cx, cy, r, a0, da = s
        # cut the arc where it turns around in y, so each part is monotone
        cuts = [0.0, abs(da)]
        sgn = 1.0 if da > 0 else -1.0
        for k in (-1.5, -0.5, 0.5, 1.5, 2.5, 3.5):
            d = _in_span(a0, da, k * math.pi)
            if d is not None and 1e-12 < d < abs(da) - 1e-12:
                cuts.append(d)
        cuts.sort()
        for i in range(len(cuts) - 1):
            b0, b1 = a0 + sgn * cuts[i], a0 + sgn * cuts[i + 1]
            y0, y1 = cy + r * math.sin(b0), cy + r * math.sin(b1)
            if (y0 <= py) != (y1 <= py):
                h2 = r * r - (py - cy) ** 2
                h = math.sqrt(h2) if h2 > 0 else 0.0
                x = cx + h if math.cos((b0 + b1) / 2) > 0 else cx - h
                if x > px:
                    wn += 1 if y1 > y0 else -1
    for x0, y0, x1, y1 in lines:
        if (y0 <= py) != (y1 <= py):
            x = x0 + (py - y0) * (x1 - x0) / (y1 - y0)
            if x > px:
                wn += 1 if y1 > y0 else -1
    return wn


# ---------------------------------------------------------------- curves -> lines + arcs

def _arc_from(px, py, tx, ty, qx, qy):
    """Arc leaving (px,py) along unit tangent (tx,ty) and passing through (qx,qy)."""
    nx, ny = -ty, tx
    cxv, cyv = qx - px, qy - py
    c2 = cxv * cxv + cyv * cyv
    den = 2 * (nx * cxv + ny * cyv)
    if c2 < 1e-18:
        return None
    if abs(den) < 1e-9 * math.sqrt(c2) or abs(c2 / den) > 1e5:
        return ("L", px, py, qx, qy)
    rs = c2 / den
    cx, cy = px + nx * rs, py + ny * rs
    a0 = math.atan2(py - cy, px - cx)
    a1 = math.atan2(qy - cy, qx - cx)
    if rs > 0:
        da = (a1 - a0) % TAU
    else:
        da = -((a0 - a1) % TAU)
    return ("A", cx, cy, abs(rs), a0, da)


def _reverse(s):
    if s[0] == "L":
        return ("L", s[3], s[4], s[1], s[2])
    return ("A", s[1], s[2], s[3], s[4] + s[5], -s[5])


def _biarc(p0, t0, p1, t1):
    vx, vy = p1[0] - p0[0], p1[1] - p0[1]
    vv = vx * vx + vy * vy
    if vv < 1e-18:
        return []
    tx, ty = t0[0] + t1[0], t0[1] + t1[1]
    vt = vx * tx + vy * ty
    den = 2 * (1 - (t0[0] * t1[0] + t0[1] * t1[1]))
    if den < 1e-10:
        vt1 = vx * t1[0] + vy * t1[1]
        if abs(vt1) < 1e-10 * math.sqrt(vv):
            pm = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
            a = _arc_from(p0[0], p0[1], t0[0], t0[1], pm[0], pm[1])
            b = _arc_from(p1[0], p1[1], -t1[0], -t1[1], pm[0], pm[1])
            return [s for s in (a, _reverse(b) if b else None) if s]
        d = vv / (4 * vt1)
    else:
        d = (-vt + math.sqrt(vt * vt + den * vv)) / den
    pm = ((p0[0] + d * t0[0] + p1[0] - d * t1[0]) / 2, (p0[1] + d * t0[1] + p1[1] - d * t1[1]) / 2)
    a = _arc_from(p0[0], p0[1], t0[0], t0[1], pm[0], pm[1])
    b = _arc_from(p1[0], p1[1], -t1[0], -t1[1], pm[0], pm[1])
    return [s for s in (a, _reverse(b) if b else None) if s]


def _cubic_tangents(c):
    _, x0, y0, x1, y1, x2, y2, x3, y3 = c
    pts = [(x0, y0), (x1, y1), (x2, y2), (x3, y3)]

    def first(seq):
        for i in range(1, 4):
            dx, dy = seq[i][0] - seq[0][0], seq[i][1] - seq[0][1]
            n = math.hypot(dx, dy)
            if n > 1e-9:
                return dx / n, dy / n
        return None

    a = first(pts)
    b = first(pts[::-1])
    return a, ((-b[0], -b[1]) if b else None)


def _split_cubic(c):
    _, x0, y0, x1, y1, x2, y2, x3, y3 = c
    ax, ay = (x0 + x1) / 2, (y0 + y1) / 2
    bx, by = (x1 + x2) / 2, (y1 + y2) / 2
    cx, cy = (x2 + x3) / 2, (y2 + y3) / 2
    dx, dy = (ax + bx) / 2, (ay + by) / 2
    ex, ey = (bx + cx) / 2, (by + cy) / 2
    fx, fy = (dx + ex) / 2, (dy + ey) / 2
    return ("C", x0, y0, ax, ay, dx, dy, fx, fy), ("C", fx, fy, ex, ey, cx, cy, x3, y3)


def cubic_to_arcs(c, tol=0.02, depth=0, soft=None):
    """Fit a cubic with lines and circular arcs, never straying more than `tol`.

    Centres of the fitted arcs are added to `soft`, so that the outline can later
    recognise "this run of little arcs is really one curve" and hand back a cubic.
    """
    out = _cubic_to_arcs(c, tol, depth)
    if soft is not None:
        for seg in out:
            if seg[0] == "A":
                soft.add((seg[1], seg[2]))
    return out


def _cubic_to_arcs(c, tol, depth):
    t0, t1 = _cubic_tangents(c)
    p0, p1 = (c[1], c[2]), (c[7], c[8])
    if t0 is None or math.hypot(p1[0] - p0[0], p1[1] - p0[1]) < 1e-9:
        return []
    # already straight?
    chord = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    ux, uy = (p1[0] - p0[0]) / chord, (p1[1] - p0[1]) / chord
    off = max(abs((c[3] - p0[0]) * uy - (c[4] - p0[1]) * ux), abs((c[5] - p0[0]) * uy - (c[6] - p0[1]) * ux))
    along = [(c[3] - p0[0]) * ux + (c[4] - p0[1]) * uy, (c[5] - p0[0]) * ux + (c[6] - p0[1]) * uy]
    if off < tol * 0.25 and -1e-9 <= along[0] <= chord + 1e-9 and -1e-9 <= along[1] <= chord + 1e-9:
        return [("L", p0[0], p0[1], p1[0], p1[1])]
    fit = _biarc(p0, t0, p1, t1)
    if fit and depth >= 1:
        err = 0.0
        for i in range(1, 12):
            qx, qy = cubic_point(c, i / 12.0)
            err = max(err, min(_dist_seg(s, qx, qy) for s in fit))
            if err > tol:
                break
        total = sum(abs(s[5]) for s in fit if s[0] == "A")
        if err <= tol and total < math.pi * 1.2:
            return fit
    if depth >= 9:
        return fit or [("L", p0[0], p0[1], p1[0], p1[1])]
    a, b = _split_cubic(c)
    return _cubic_to_arcs(a, tol, depth + 1) + _cubic_to_arcs(b, tol, depth + 1)


def simplify(subpaths, tol=0.02, soft=None):
    """Replace every cubic with lines/arcs and drop degenerate segments."""
    out = []
    for segs, closed in subpaths:
        ns = []
        for s in segs:
            if s[0] == "C":
                ns.extend(cubic_to_arcs(s, tol, 0, soft))
            elif s[0] == "L":
                if math.hypot(s[3] - s[1], s[4] - s[2]) > 1e-9:
                    ns.append(s)
            elif s[3] > 1e-9 and abs(s[5]) > 1e-12:
                ns.append(s)
        if ns:
            out.append((ns, closed))
    return out


# ---------------------------------------------------------------- candidate pieces

def _tangent_at(s, end):
    """Unit direction of travel at the start (end=0) or end (end=1) of a segment."""
    if s[0] == "L":
        dx, dy = s[3] - s[1], s[4] - s[2]
        n = math.hypot(dx, dy)
        return dx / n, dy / n
    a = s[4] + (s[5] if end else 0.0)
    sg = 1.0 if s[5] > 0 else -1.0
    return -math.sin(a) * sg, math.cos(a) * sg


def _candidates(ops):
    cands = []
    seen_circles = set()

    def circle(x, y, r):
        key = (round(x / SNAP), round(y / SNAP), round(r / SNAP))
        if key not in seen_circles:
            seen_circles.add(key)
            cands.append(("A", x, y, r, 0.0, TAU))

    for op in ops:
        hw = op.hw
        for segs, closed in op.subpaths:
            if not segs:
                continue
            if hw > 0:
                n = len(segs)
                for i, s in enumerate(segs):
                    if s[0] == "L":
                        dx, dy = s[3] - s[1], s[4] - s[2]
                        ln = math.hypot(dx, dy)
                        ox, oy = -dy / ln * hw, dx / ln * hw
                        cands.append(("L", s[1] + ox, s[2] + oy, s[3] + ox, s[4] + oy))
                        cands.append(("L", s[1] - ox, s[2] - oy, s[3] - ox, s[4] - oy))
                    else:
                        cands.append(("A", s[1], s[2], s[3] + hw, s[4], s[5]))
                        if s[3] - hw > 1e-6:
                            cands.append(("A", s[1], s[2], s[3] - hw, s[4], s[5]))
                    # a round join or cap is needed wherever the direction breaks
                    ex, ey = seg_end(s)
                    nxt = segs[i + 1] if i + 1 < n else None
                    if nxt is None:
                        sx, sy = seg_start(segs[0])
                        if math.hypot(sx - ex, sy - ey) < SNAP:
                            nxt = segs[0]
                    if nxt is None:
                        circle(ex, ey, hw)
                    else:
                        t0, t1 = _tangent_at(s, 1), _tangent_at(nxt, 0)
                        if t0[0] * t1[0] + t0[1] * t1[1] < 1 - 1e-9:
                            circle(ex, ey, hw)
                    if i == 0:
                        sx, sy = seg_start(s)
                        lx, ly = seg_end(segs[-1])
                        if math.hypot(sx - lx, sy - ly) >= SNAP:
                            circle(sx, sy, hw)
            if op.filled:
                cands.extend(segs)
                sx, sy = seg_start(segs[0])
                ex, ey = seg_end(segs[-1])
                if math.hypot(sx - ex, sy - ey) > SNAP:
                    cands.append(("L", ex, ey, sx, sy))
    return cands


def _box(c):
    if c[0] == "L":
        return (min(c[1], c[3]), min(c[2], c[4]), max(c[1], c[3]), max(c[2], c[4]))
    return (c[1] - c[3], c[2] - c[3], c[1] + c[3], c[2] + c[3])


def _param(c, x, y):
    """Position 0..1 of (x, y) along piece c, or None if the point is not on it."""
    if c[0] == "L":
        dx, dy = c[3] - c[1], c[4] - c[2]
        L2 = dx * dx + dy * dy
        t = ((x - c[1]) * dx + (y - c[2]) * dy) / L2
        tol = SNAP / math.sqrt(L2)
        if t < -tol or t > 1 + tol:
            return None
        if abs((x - c[1]) * dy - (y - c[2]) * dx) / math.sqrt(L2) > 2 * GRAZE:
            return None
        return min(1.0, max(0.0, t))
    _, cx, cy, r, a0, da = c
    if abs(math.hypot(x - cx, y - cy) - r) > 2 * GRAZE:
        return None
    ang = math.atan2(y - cy, x - cx)
    if abs(da) >= TAU - 1e-12:
        return ((ang - a0) % TAU) / TAU
    d = _in_span(a0, da, ang, SNAP / r)
    if d is None:
        return None
    return min(1.0, d / abs(da))


def _ends(c):
    return [seg_start(c), seg_end(c)]


def _meet(c1, c2):
    """Points where the supporting line/circle of two pieces meet (unfiltered)."""
    k1, k2 = c1[0], c2[0]
    if k1 == "L" and k2 == "L":
        px, py, rx, ry = c1[1], c1[2], c1[3] - c1[1], c1[4] - c1[2]
        qx, qy, sx, sy = c2[1], c2[2], c2[3] - c2[1], c2[4] - c2[2]
        rxs = rx * sy - ry * sx
        lr, ls = math.hypot(rx, ry), math.hypot(sx, sy)
        if abs(rxs) < 1e-10 * lr * ls:
            if abs((qx - px) * ry - (qy - py) * rx) / lr < GRAZE:
                return _ends(c1) + _ends(c2)
            return []
        t = ((qx - px) * sy - (qy - py) * sx) / rxs
        return [(px + t * rx, py + t * ry)]
    if k1 == "L" or k2 == "L":
        ln, ci = (c1, c2) if k1 == "L" else (c2, c1)
        px, py, dx, dy = ln[1], ln[2], ln[3] - ln[1], ln[4] - ln[2]
        cx, cy, r = ci[1], ci[2], ci[3]
        a = dx * dx + dy * dy
        fx, fy = px - cx, py - cy
        t0 = -(fx * dx + fy * dy) / a
        nx, ny = fx + t0 * dx, fy + t0 * dy     # centre -> foot of perpendicular
        depth = r - math.hypot(nx, ny)          # how far the line dips into the circle
        if depth < -GRAZE:
            return []
        if depth <= GRAZE:
            return [(px + t0 * dx, py + t0 * dy)]
        h = math.sqrt((r * r - (nx * nx + ny * ny)) / a)
        return [(px + (t0 - h) * dx, py + (t0 - h) * dy), (px + (t0 + h) * dx, py + (t0 + h) * dy)]
    x1, y1, r1 = c1[1], c1[2], c1[3]
    x2, y2, r2 = c2[1], c2[2], c2[3]
    d = math.hypot(x2 - x1, y2 - y1)
    if d < GRAZE and abs(r1 - r2) < GRAZE:
        return _ends(c1) + _ends(c2)
    outer = r1 + r2 - d            # overlap when the circles sit side by side
    inner = d - abs(r1 - r2)       # overlap when one sits inside the other
    if outer < -GRAZE or inner < -GRAZE or d < SNAP:
        return []
    ux, uy = (x2 - x1) / d, (y2 - y1) / d
    if outer <= GRAZE:
        return [(x1 + r1 * ux, y1 + r1 * uy)]
    if inner <= GRAZE:
        k = r1 if r1 > r2 else -r1
        return [(x1 + k * ux, y1 + k * uy)]
    a = (d * d + r1 * r1 - r2 * r2) / (2 * d)
    h = math.sqrt(max(0.0, r1 * r1 - a * a))
    mx, my = x1 + a * ux, y1 + a * uy
    return [(mx - h * uy, my + h * ux), (mx + h * uy, my - h * ux)]


def _length(c):
    if c[0] == "L":
        return math.hypot(c[3] - c[1], c[4] - c[2])
    return c[3] * abs(c[5])


def _sub(c, t0, t1):
    if c[0] == "L":
        dx, dy = c[3] - c[1], c[4] - c[2]
        return ("L", c[1] + t0 * dx, c[2] + t0 * dy, c[1] + t1 * dx, c[2] + t1 * dy)
    return ("A", c[1], c[2], c[3], c[4] + t0 * c[5], (t1 - t0) * c[5])


def _point_normal(c, f):
    """Point at fraction f of piece c and the unit normal on its left (inside) side."""
    if c[0] == "L":
        dx, dy = c[3] - c[1], c[4] - c[2]
        ln = math.hypot(dx, dy)
        return c[1] + f * dx, c[2] + f * dy, -dy / ln, dx / ln
    a = c[4] + f * c[5]
    ca, sa = math.cos(a), math.sin(a)
    sg = 1.0 if c[5] > 0 else -1.0
    # direction of travel is (-sin, cos)*sg; rotate it a quarter turn to get the normal
    return c[1] + c[3] * ca, c[2] + c[3] * sa, -ca * sg, -sa * sg


# ---------------------------------------------------------------- the outline

LOOSE = 0.05      # widest gap the chaining will step across
DROPPED = []      # chains that never closed (callers may inspect this to warn)

def outline(ops, soft=None):
    """Return closed subpaths bounding everything the ops paint.

    The result is lines and circular arcs, except where a run of arcs listed in
    `soft` (curve approximations) can be replaced by a cubic within REFIT units.
    """
    ops = [op for op in ops if op.subpaths and (op.hw > 0 or op.filled)]
    if not ops:
        return []
    cands = _candidates(ops)
    boxes = [_box(c) for c in cands]
    n = len(cands)
    cuts = [[] for _ in range(n)]
    order = sorted(range(n), key=lambda i: boxes[i][0])
    for oi in range(n):
        i = order[oi]
        bi = boxes[i]
        for oj in range(oi + 1, n):
            j = order[oj]
            bj = boxes[j]
            if bj[0] > bi[2] + SNAP:
                break
            if bj[1] > bi[3] + SNAP or bj[3] < bi[1] - SNAP:
                continue
            for x, y in _meet(cands[i], cands[j]):
                ti = _param(cands[i], x, y)
                if ti is None:
                    continue
                tj = _param(cands[j], x, y)
                if tj is None:
                    continue
                cuts[i].append(ti)
                cuts[j].append(tj)

    pieces = []
    for c, ts in zip(cands, cuts):
        ln = _length(c)
        if ln < SNAP:
            continue
        full = c[0] == "A" and abs(c[5]) >= TAU - 1e-12
        tol = 2 * SNAP / ln
        ts = sorted(ts)
        uniq = []
        for t in ts:
            if not uniq or t - uniq[-1] > tol:
                uniq.append(t)
        if full:
            if len(uniq) > 1 and (uniq[0] + 1 - uniq[-1]) <= tol:
                uniq.pop()
            if not uniq:
                pieces.append(c)
                continue
            for k in range(len(uniq)):
                a, b = uniq[k], uniq[(k + 1) % len(uniq)]
                if k == len(uniq) - 1:
                    b += 1.0
                pieces.append(_sub(c, a, b))
        else:
            uniq = [t for t in uniq if tol < t < 1 - tol]
            bounds = [0.0] + uniq + [1.0]
            for k in range(len(bounds) - 1):
                pieces.append(_sub(c, bounds[k], bounds[k + 1]))

    # keep the pieces with paint on exactly one side, turned so paint is on the left
    kept = {}
    for p in pieces:
        ln = _length(p)
        if ln < 4 * SNAP:
            continue
        votes = 0
        for f in (0.5, 0.2764, 0.7236):
            x, y, nx, ny = _point_normal(p, f)
            left = painted(ops, x + nx * PROBE, y + ny * PROBE)
            right = painted(ops, x - nx * PROBE, y - ny * PROBE)
            if left and not right:
                votes += 1
            elif right and not left:
                votes -= 1
        if abs(votes) < 2:
            continue
        if votes < 0:
            p = _reverse(p)
        sx, sy = seg_start(p)
        ex, ey = seg_end(p)
        mx, my, _, _ = _point_normal(p, 0.5)
        key = (round(sx / 1e-5), round(sy / 1e-5), round(mx / 1e-5), round(my / 1e-5),
               round(ex / 1e-5), round(ey / 1e-5))
        kept.setdefault(key, p)
    loops = _chain(list(kept.values()))
    if soft:
        loops = [(refit(segs, soft), closed) for segs, closed in loops]
    return loops


def _chain(pieces):
    """Join oriented pieces end to start into closed loops."""
    grid = {}

    def cell(x, y):
        return int(math.floor(x / 1e-4)), int(math.floor(y / 1e-4))

    for i, p in enumerate(pieces):
        x, y = seg_start(p)
        grid.setdefault(cell(x, y), []).append(i)
    used = [False] * len(pieces)

    def next_piece(cur):
        ex, ey = seg_end(cur)
        tx, ty = _tangent_at(cur, 1)
        cx, cy = cell(ex, ey)
        best, best_turn = None, None
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for j in grid.get((gx, gy), ()):
                    if used[j]:
                        continue
                    sx, sy = seg_start(pieces[j])
                    if math.hypot(sx - ex, sy - ey) > 5e-5:
                        continue
                    ox, oy = _tangent_at(pieces[j], 0)
                    turn = math.atan2(tx * oy - ty * ox, tx * ox + ty * oy)
                    if best is None or turn > best_turn:
                        best, best_turn = j, turn
        if best is None:
            # imprecise input can leave a hairline gap; step across to the nearest start
            near = LOOSE
            for j, p in enumerate(pieces):
                if not used[j]:
                    sx, sy = seg_start(p)
                    dist = math.hypot(sx - ex, sy - ey)
                    if dist < near:
                        best, near = j, dist
        return best

    loops = []
    for i in range(len(pieces)):
        if used[i]:
            continue
        used[i] = True
        loop = [pieces[i]]
        sx, sy = seg_start(pieces[i])
        ok = False
        while True:
            ex, ey = seg_end(loop[-1])
            if math.hypot(ex - sx, ey - sy) <= 5e-5 and (len(loop) > 1 or _length(loop[0]) > 1e-3):
                ok = True
                break
            j = next_piece(loop[-1])
            if j is None:
                ok = math.hypot(ex - sx, ey - sy) < LOOSE and len(loop) > 1
                break
            used[j] = True
            loop.append(pieces[j])
        if ok:
            loops.append((_tidy(loop), True))
        elif sum(_length(p) for p in loop) > 0.5:
            DROPPED.append(loop)
    # biggest loops first: stable, readable output
    loops.sort(key=lambda sp: -_loop_extent(sp[0]))
    return loops


def _loop_extent(segs):
    xs, ys = [], []
    for s in segs:
        b = _box(s)
        xs += [b[0], b[2]]
        ys += [b[1], b[3]]
    return (max(xs) - min(xs)) * (max(ys) - min(ys)) if xs else 0.0


def _tidy(loop):
    """Merge neighbours that lie on the same line or circle and make the ends meet exactly."""
    out = []
    for s in loop:
        if out and _same_support(out[-1], s):
            out[-1] = _merge(out[-1], s)
        else:
            out.append(s)
    while len(out) > 1 and _same_support(out[-1], out[0]):
        out[0] = _merge(out[-1], out[0])
        out.pop()
    # start each loop at a corner-ish, well-defined point: the top-most, then left-most start
    k = min(range(len(out)), key=lambda i: (round(seg_start(out[i])[1], 3), round(seg_start(out[i])[0], 3)))
    out = out[k:] + out[:k]
    return out


def _same_support(a, b):
    if a[0] != b[0]:
        return False
    if a[0] == "L":
        ta, tb = _tangent_at(a, 1), _tangent_at(b, 0)
        return ta[0] * tb[0] + ta[1] * tb[1] > 1 - 1e-10
    return (abs(a[1] - b[1]) < 1e-5 and abs(a[2] - b[2]) < 1e-5 and abs(a[3] - b[3]) < 1e-5
            and (a[5] > 0) == (b[5] > 0) and abs(a[5]) + abs(b[5]) <= TAU + 1e-9)


def _merge(a, b):
    if a[0] == "L":
        return ("L", a[1], a[2], b[3], b[4])
    return ("A", a[1], a[2], a[3], a[4], a[5] + b[5])


# ---------------------------------------------------------------- arcs back to curves

REFIT = 0.03      # how far a refitted cubic may stray from the arcs it replaces


def refit(loop, soft, tol=REFIT):
    """Replace smooth runs of curve-approximating arcs with cubic beziers.

    A bezier in the skeleton becomes a dozen small arcs on the way in; left alone,
    its outline would come out as a dozen nodes where a designer would draw two.
    """
    n = len(loop)
    is_soft = [s[0] == "A" and (s[1], s[2]) in soft for s in loop]
    if not any(is_soft):
        return loop

    def smooth(i, j):
        a, b = _tangent_at(loop[i], 1), _tangent_at(loop[j], 0)
        return a[0] * b[0] + a[1] * b[1] > 0.99985 and (loop[i][5] > 0) == (loop[j][5] > 0)

    # start walking at a place where a run cannot wrap around the end of the list
    start = 0
    for i in range(n):
        if not (is_soft[i] and is_soft[i - 1] and smooth(i - 1, i)):
            start = i
            break
    order = [(start + k) % n for k in range(n)]
    out = []
    k = 0
    while k < n:
        i = order[k]
        if not is_soft[i]:
            out.append(loop[i])
            k += 1
            continue
        run = [loop[i]]
        while k + 1 < n and is_soft[order[k + 1]] and smooth(order[k], order[k + 1]):
            k += 1
            run.append(loop[order[k]])
        k += 1
        if len(run) < 2:
            out.extend(run)
        else:
            out.extend(_fit_run(run, tol))
    return out


def _fit_run(run, tol):
    lens = [_length(s) for s in run]
    total = sum(lens)
    turn = sum(abs(s[5]) for s in run)

    def at(d):
        """Point and unit tangent at distance d along the run."""
        for s, ln in zip(run, lens):
            if d <= ln or s is run[-1]:
                f = min(1.0, max(0.0, d / ln))
                a = s[4] + f * s[5]
                sg = 1.0 if s[5] > 0 else -1.0
                return (s[1] + s[3] * math.cos(a), s[2] + s[3] * math.sin(a), -math.sin(a) * sg, math.cos(a) * sg)
            d -= ln

    def fit(d0, d1, depth):
        x0, y0, tx0, ty0 = at(d0)
        x3, y3, tx3, ty3 = at(d1)
        m = 12
        pts = [at(d0 + (d1 - d0) * i / m)[:2] for i in range(m + 1)]
        us = [i / float(m) for i in range(m + 1)]
        best = None
        for _ in range(4):
            c11 = c12 = c22 = r1 = r2 = 0.0
            for (qx, qy), u in zip(pts, us):
                b0, b1, b2, b3 = (1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u * u * (1 - u), u ** 3
                a1x, a1y = tx0 * b1, ty0 * b1
                a2x, a2y = -tx3 * b2, -ty3 * b2
                c11 += a1x * a1x + a1y * a1y
                c12 += a1x * a2x + a1y * a2y
                c22 += a2x * a2x + a2y * a2y
                ex = qx - (x0 * (b0 + b1) + x3 * (b2 + b3))
                ey = qy - (y0 * (b0 + b1) + y3 * (b2 + b3))
                r1 += ex * a1x + ey * a1y
                r2 += ex * a2x + ey * a2y
            det = c11 * c22 - c12 * c12
            chord = math.hypot(x3 - x0, y3 - y0)
            if abs(det) > 1e-12:
                a, b = (r1 * c22 - r2 * c12) / det, (c11 * r2 - c12 * r1) / det
            else:
                a = b = chord / 3
            if a < chord * 0.05 or b < chord * 0.05:
                a = b = chord / 3
            cub = ("C", x0, y0, x0 + a * tx0, y0 + a * ty0, x3 - b * tx3, y3 - b * ty3, x3, y3)
            err = 0.0
            for (qx, qy), u in zip(pts, us):
                px, py = cubic_point(cub, u)
                err = max(err, math.hypot(px - qx, py - qy))
            if best is None or err < best[0]:
                best = (err, cub)
            if err <= tol * 0.5:
                break
            # slide each sample's parameter towards the nearest point on the curve
            nu = []
            for (qx, qy), u in zip(pts, us):
                px, py = cubic_point(cub, u)
                h = 1e-4
                p1 = cubic_point(cub, min(1.0, u + h))
                p0 = cubic_point(cub, max(0.0, u - h))
                dxu, dyu = (p1[0] - p0[0]) / (2 * h), (p1[1] - p0[1]) / (2 * h)
                den = dxu * dxu + dyu * dyu
                if den > 1e-12:
                    u = min(1.0, max(0.0, u - ((px - qx) * dxu + (py - qy) * dyu) / den))
                nu.append(u)
            nu[0], nu[-1] = 0.0, 1.0
            us = nu
        if best[0] <= tol or depth >= 6:
            return [best[1]]
        mid = (d0 + d1) / 2
        return fit(d0, mid, depth + 1) + fit(mid, d1, depth + 1)

    # a cubic follows about a quarter turn well; give it no more than that
    parts = max(1, int(math.ceil(turn / (math.pi / 2) - 1e-9)))
    out = []
    for k in range(parts):
        out.extend(fit(total * k / parts, total * (k + 1) / parts, 0))
    return out
