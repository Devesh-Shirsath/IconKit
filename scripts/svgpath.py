"""SVG path + basic-shape parsing into plain geometry.

Everything downstream works on three segment kinds, all in absolute user units:

    ("L", x0, y0, x1, y1)                       straight line
    ("A", cx, cy, r, a0, da)                    circular arc, start angle a0, signed sweep da
    ("C", x0, y0, x1, y1, x2, y2, x3, y3)       cubic bezier

Angles are radians in SVG's y-down frame, so a positive `da` is what SVG calls
sweep-flag=1 (clockwise on screen). A subpath is (segments, closed).

Standard library only.
"""
import math
import re

TAU = 2 * math.pi
_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_CMD = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]")
_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def _tokens(d):
    """Yield (command, [numbers]) honouring implicit repeats and glued arc flags."""
    pos = 0
    n = len(d)
    cmd = None
    while pos < n:
        ch = d[pos]
        if ch in " ,\t\r\n":
            pos += 1
            continue
        if _CMD.match(ch):
            cmd = ch
            pos += 1
            if cmd in "Zz":
                yield cmd, []
            continue
        if cmd is None:
            raise ValueError("path data must start with a command: %r" % d[:20])
        need = _ARGS[cmd.upper()]
        args = []
        while len(args) < need:
            while pos < n and d[pos] in " ,\t\r\n":
                pos += 1
            if cmd in "Aa" and len(args) in (3, 4):
                # flags are single characters and may be glued to what follows
                if pos >= n or d[pos] not in "01":
                    raise ValueError("bad arc flag in %r" % d[max(0, pos - 20):pos + 5])
                args.append(float(d[pos]))
                pos += 1
                continue
            m = _NUM.match(d, pos)
            if not m:
                raise ValueError("bad number in path near %r" % d[max(0, pos - 20):pos + 10])
            args.append(float(m.group()))
            pos = m.end()
        yield cmd, args
        if cmd == "M":
            cmd = "L"
        elif cmd == "m":
            cmd = "l"


def arc_center(x1, y1, rx, ry, phi_deg, large, sweep, x2, y2):
    """Endpoint -> centre parameterisation (SVG 1.1 F.6.5). Returns cx, cy, rx, ry, phi, a0, da."""
    phi = math.radians(phi_deg)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2.0, (y1 - y2) / 2.0
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    rx, ry = abs(rx), abs(ry)
    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1:
        s = math.sqrt(lam)
        rx, ry = rx * s, ry * s
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if bool(large) == bool(sweep):
        co = -co
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2.0
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2.0
    a0 = math.atan2((y1p - cyp) / ry, (x1p - cxp) / rx)
    a1 = math.atan2((-y1p - cyp) / ry, (-x1p - cxp) / rx)
    da = a1 - a0
    if sweep and da < 0:
        da += TAU
    elif not sweep and da > 0:
        da -= TAU
    return cx, cy, rx, ry, phi, a0, da


def ellipse_arc_to_cubics(cx, cy, rx, ry, phi, a0, da):
    """Approximate an elliptical arc with cubics (<= 90 degrees each)."""
    n = max(1, int(math.ceil(abs(da) / (math.pi / 2) - 1e-9)))
    step = da / n
    k = 4.0 / 3.0 * math.tan(step / 4.0)
    cp, sp = math.cos(phi), math.sin(phi)

    def pt(a):
        x, y = rx * math.cos(a), ry * math.sin(a)
        return cx + cp * x - sp * y, cy + sp * x + cp * y

    def der(a):
        x, y = -rx * math.sin(a), ry * math.cos(a)
        return cp * x - sp * y, sp * x + cp * y

    out = []
    a = a0
    for _ in range(n):
        b = a + step
        p0, p3 = pt(a), pt(b)
        d0, d3 = der(a), der(b)
        out.append(("C", p0[0], p0[1], p0[0] + k * d0[0], p0[1] + k * d0[1],
                    p3[0] - k * d3[0], p3[1] - k * d3[1], p3[0], p3[1]))
        a = b
    return out


def parse_path(d):
    """Parse path data into a list of (segments, closed) subpaths."""
    subs = []
    segs = []
    x = y = sx = sy = 0.0
    lcx = lcy = None  # last cubic control (for S)
    lqx = lqy = None  # last quadratic control (for T)

    def flush(closed):
        if segs:
            subs.append((list(segs), closed))
        del segs[:]

    for cmd, a in _tokens(d):
        up = cmd.upper()
        rel = cmd != up
        if up == "M":
            flush(False)
            x, y = (x + a[0], y + a[1]) if rel else (a[0], a[1])
            sx, sy = x, y
            lcx = lqx = None
            continue
        if up == "Z":
            if (abs(x - sx) > 1e-9 or abs(y - sy) > 1e-9):
                segs.append(("L", x, y, sx, sy))
            flush(True)
            x, y = sx, sy
            lcx = lqx = None
            continue
        if up == "L":
            nx, ny = (x + a[0], y + a[1]) if rel else (a[0], a[1])
            segs.append(("L", x, y, nx, ny))
            lcx = lqx = None
        elif up == "H":
            nx, ny = (x + a[0] if rel else a[0]), y
            segs.append(("L", x, y, nx, ny))
            lcx = lqx = None
        elif up == "V":
            nx, ny = x, (y + a[0] if rel else a[0])
            segs.append(("L", x, y, nx, ny))
            lcx = lqx = None
        elif up == "C":
            ox, oy = (x, y) if rel else (0.0, 0.0)
            x1, y1, x2, y2, nx, ny = (a[0] + ox, a[1] + oy, a[2] + ox, a[3] + oy, a[4] + ox, a[5] + oy)
            segs.append(("C", x, y, x1, y1, x2, y2, nx, ny))
            lcx, lcy, lqx = x2, y2, None
        elif up == "S":
            ox, oy = (x, y) if rel else (0.0, 0.0)
            x1, y1 = (2 * x - lcx, 2 * y - lcy) if lcx is not None else (x, y)
            x2, y2, nx, ny = a[0] + ox, a[1] + oy, a[2] + ox, a[3] + oy
            segs.append(("C", x, y, x1, y1, x2, y2, nx, ny))
            lcx, lcy, lqx = x2, y2, None
        elif up in "QT":
            ox, oy = (x, y) if rel else (0.0, 0.0)
            if up == "Q":
                qx, qy, nx, ny = a[0] + ox, a[1] + oy, a[2] + ox, a[3] + oy
            else:
                qx, qy = (2 * x - lqx, 2 * y - lqy) if lqx is not None else (x, y)
                nx, ny = a[0] + ox, a[1] + oy
            segs.append(("C", x, y, x + 2.0 / 3 * (qx - x), y + 2.0 / 3 * (qy - y),
                         nx + 2.0 / 3 * (qx - nx), ny + 2.0 / 3 * (qy - ny), nx, ny))
            lqx, lqy, lcx = qx, qy, None
        elif up == "A":
            nx, ny = (x + a[5], y + a[6]) if rel else (a[5], a[6])
            if abs(nx - x) > 1e-9 or abs(ny - y) > 1e-9:
                if a[0] == 0 or a[1] == 0:
                    segs.append(("L", x, y, nx, ny))
                else:
                    cx, cy, rx, ry, phi, a0, da = arc_center(x, y, a[0], a[1], a[2], a[3], a[4], nx, ny)
                    if abs(rx - ry) < 1e-9:
                        segs.append(("A", cx, cy, rx, a0 + phi, da))
                    else:
                        segs.extend(ellipse_arc_to_cubics(cx, cy, rx, ry, phi, a0, da))
            lcx = lqx = None
        x, y = nx, ny
    flush(False)
    return subs


# ---------------------------------------------------------------- shapes

def circle_subpath(cx, cy, r):
    return ([("A", cx, cy, r, 0.0, math.pi), ("A", cx, cy, r, math.pi, math.pi)], True)


def ellipse_subpath(cx, cy, rx, ry):
    if abs(rx - ry) < 1e-9:
        return circle_subpath(cx, cy, rx)
    return (ellipse_arc_to_cubics(cx, cy, rx, ry, 0.0, 0.0, TAU), True)


def rect_subpath(x, y, w, h, rx=0.0, ry=None):
    if ry is None:
        ry = rx
    rx, ry = min(rx, w / 2.0), min(ry, h / 2.0)
    if rx <= 0 or ry <= 0:
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        return ([("L", pts[i][0], pts[i][1], pts[(i + 1) % 4][0], pts[(i + 1) % 4][1]) for i in range(4)], True)
    if abs(rx - ry) > 1e-9:
        d = ("M%g,%gH%gA%g,%g,0,0,1,%g,%gV%gA%g,%g,0,0,1,%g,%gH%gA%g,%g,0,0,1,%g,%gV%gA%g,%g,0,0,1,%g,%gZ" % (
            x + rx, y, x + w - rx, rx, ry, x + w, y + ry, y + h - ry, rx, ry, x + w - rx, y + h,
            x + rx, rx, ry, x, y + h - ry, y + ry, rx, ry, x + rx, y))
        return parse_path(d)[0]
    r = rx
    hp = math.pi / 2
    segs = []
    if w - 2 * r > 1e-9:
        segs.append(("L", x + r, y, x + w - r, y))
    segs.append(("A", x + w - r, y + r, r, -hp, hp))
    if h - 2 * r > 1e-9:
        segs.append(("L", x + w, y + r, x + w, y + h - r))
    segs.append(("A", x + w - r, y + h - r, r, 0.0, hp))
    if w - 2 * r > 1e-9:
        segs.append(("L", x + w - r, y + h, x + r, y + h))
    segs.append(("A", x + r, y + h - r, r, hp, hp))
    if h - 2 * r > 1e-9:
        segs.append(("L", x, y + h - r, x, y + r))
    segs.append(("A", x + r, y + r, r, math.pi, hp))
    return (segs, True)


def poly_subpath(points, closed):
    segs = []
    for i in range(len(points) - 1):
        (x0, y0), (x1, y1) = points[i], points[i + 1]
        if abs(x0 - x1) > 1e-9 or abs(y0 - y1) > 1e-9:
            segs.append(("L", x0, y0, x1, y1))
    if closed and len(points) > 2:
        (x0, y0), (x1, y1) = points[-1], points[0]
        if abs(x0 - x1) > 1e-9 or abs(y0 - y1) > 1e-9:
            segs.append(("L", x0, y0, x1, y1))
    return (segs, closed)


# ---------------------------------------------------------------- segment helpers

def seg_start(s):
    if s[0] == "A":
        return s[1] + s[3] * math.cos(s[4]), s[2] + s[3] * math.sin(s[4])
    return s[1], s[2]


def seg_end(s):
    if s[0] == "A":
        a = s[4] + s[5]
        return s[1] + s[3] * math.cos(a), s[2] + s[3] * math.sin(a)
    return s[-2], s[-1]


def cubic_point(s, t):
    _, x0, y0, x1, y1, x2, y2, x3, y3 = s
    mt = 1 - t
    a, b, c, d = mt * mt * mt, 3 * mt * mt * t, 3 * mt * t * t, t * t * t
    return a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3


def flatten(subpaths, tol=0.05):
    """Subpaths -> list of point lists (closed ones repeat the first point)."""
    out = []
    for segs, closed in subpaths:
        if not segs:
            continue
        pts = [seg_start(segs[0])]
        for s in segs:
            if s[0] == "L":
                pts.append((s[3], s[4]))
            elif s[0] == "A":
                _, cx, cy, r, a0, da = s
                n = max(2, int(math.ceil(abs(da) / (2 * math.acos(max(-1.0, 1 - tol / max(r, tol)))))))
                for i in range(1, n + 1):
                    a = a0 + da * i / n
                    pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
            else:
                chord = math.hypot(s[7] - s[1], s[8] - s[2])
                ctrl = (math.hypot(s[3] - s[1], s[4] - s[2]) + math.hypot(s[5] - s[3], s[6] - s[4])
                        + math.hypot(s[7] - s[5], s[8] - s[6]))
                n = max(2, int(math.ceil(math.sqrt(max(ctrl - chord, 0.0) / tol) * 2 + ctrl / 24)))
                for i in range(1, n + 1):
                    pts.append(cubic_point(s, i / float(n)))
        if closed and (abs(pts[0][0] - pts[-1][0]) > 1e-9 or abs(pts[0][1] - pts[-1][1]) > 1e-9):
            pts.append(pts[0])
        out.append(pts)
    return out


def bbox(subpaths):
    """Tight bounding box (x0, y0, x1, y1) of the geometry itself (no stroke)."""
    xs, ys = [], []
    for pts in flatten(subpaths, 0.01):
        for px, py in pts:
            xs.append(px)
            ys.append(py)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------- transforms

IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def mat_mul(m, n):
    """Compose so that mat_mul(m, n) applies n first, then m."""
    a, b, c, d, e, f = m
    a2, b2, c2, d2, e2, f2 = n
    return (a * a2 + c * b2, b * a2 + d * b2, a * c2 + c * d2, b * c2 + d * d2,
            a * e2 + c * f2 + e, b * e2 + d * f2 + f)


def parse_transform(text):
    m = IDENT
    for name, args in re.findall(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)", text or ""):
        v = [float(t) for t in _NUM.findall(args)]
        if name == "matrix" and len(v) == 6:
            t = tuple(v)
        elif name == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0.0)
        elif name == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate":
            a = math.radians(v[0])
            c, s = math.cos(a), math.sin(a)
            t = (c, s, -s, c, 0, 0)
            if len(v) == 3:
                t = mat_mul(mat_mul((1, 0, 0, 1, v[1], v[2]), t), (1, 0, 0, 1, -v[1], -v[2]))
        elif name == "skewX":
            t = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == "skewY":
            t = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        else:
            continue
        m = mat_mul(m, t)
    return m


def _apply(m, x, y):
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


def transform_subpaths(subpaths, m):
    if m == IDENT:
        return subpaths
    a, b, c, d, _, _ = m
    det = a * d - b * c
    # a similarity (rotation + uniform scale, optional mirror) keeps circles circular
    similar = abs(a * c + b * d) < 1e-9 and abs((a * a + b * b) - (c * c + d * d)) < 1e-9
    out = []
    for segs, closed in subpaths:
        ns = []
        for s in segs:
            if s[0] == "L":
                ns.append(("L",) + _apply(m, s[1], s[2]) + _apply(m, s[3], s[4]))
            elif s[0] == "C":
                ns.append(("C",) + _apply(m, s[1], s[2]) + _apply(m, s[3], s[4])
                          + _apply(m, s[5], s[6]) + _apply(m, s[7], s[8]))
            elif similar:
                k = math.sqrt(abs(det))
                rot = math.atan2(b, a)
                cx, cy = _apply(m, s[1], s[2])
                if det < 0:
                    ns.append(("A", cx, cy, s[3] * k, rot - s[4], -s[5]))
                else:
                    ns.append(("A", cx, cy, s[3] * k, s[4] + rot, s[5]))
            else:
                for cseg in ellipse_arc_to_cubics(s[1], s[2], s[3], s[3], 0.0, s[4], s[5]):
                    ns.append(("C",) + _apply(m, cseg[1], cseg[2]) + _apply(m, cseg[3], cseg[4])
                              + _apply(m, cseg[5], cseg[6]) + _apply(m, cseg[7], cseg[8]))
        out.append((ns, closed))
    return out


# ---------------------------------------------------------------- emit

def fmt(v, nd=2):
    s = ("%.*f" % (nd, v)).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def to_d(subpaths, nd=2):
    """Serialise subpaths back to compact absolute path data."""
    out = []
    for segs, closed in subpaths:
        if not segs:
            continue
        x, y = seg_start(segs[0])
        out.append("M%s,%s" % (fmt(x, nd), fmt(y, nd)))
        for s in segs:
            if s[0] == "L":
                if abs(s[4] - y) < 0.5 * 10 ** -nd:
                    out.append("H%s" % fmt(s[3], nd))
                elif abs(s[3] - x) < 0.5 * 10 ** -nd:
                    out.append("V%s" % fmt(s[4], nd))
                else:
                    out.append("L%s,%s" % (fmt(s[3], nd), fmt(s[4], nd)))
                x, y = s[3], s[4]
            elif s[0] == "A":
                _, cx, cy, r, a0, da = s
                # near a half turn, rounding the end points to two decimals moves the centre a lot;
                # quarter-turn pieces stay put (and are what design tools convert arcs to anyway)
                parts = 1 if abs(da) <= math.pi * 2 / 3 + 1e-9 else int(math.ceil(abs(da) / (math.pi / 2) - 1e-9))
                for i in range(parts):
                    b = a0 + da * (i + 1) / parts
                    x, y = cx + r * math.cos(b), cy + r * math.sin(b)
                    out.append("A%s,%s,0,%d,%d,%s,%s" % (fmt(r, nd), fmt(r, nd),
                                                         1 if abs(da) / parts > math.pi + 1e-9 else 0,
                                                         1 if da > 0 else 0, fmt(x, nd), fmt(y, nd)))
            else:
                out.append("C%s,%s,%s,%s,%s,%s" % tuple(fmt(v, nd) for v in s[3:]))
                x, y = s[7], s[8]
        if closed:
            out.append("Z")
    return "".join(out)
