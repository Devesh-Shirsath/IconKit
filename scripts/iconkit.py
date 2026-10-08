#!/usr/bin/env python3
"""IconKit - draw one stroke skeleton, get a Phosphor-style icon in all six weights.

    iconkit.py find  <words...>            does Phosphor already have this icon?
    iconkit.py sheet <names...> -o x.png   render real Phosphor icons to study them
    iconkit.py show  <name> [weight]       print a real Phosphor icon's path data
    iconkit.py build <source.svg>          six outlined SVGs + preview.png (+ --react)
    iconkit.py check <source.svg>          lint the skeleton against the Phosphor spec
    iconkit.py compare <source.svg> <name> measure a skeleton against a real icon

Python 3.8+, standard library only.
"""
import argparse
import gzip
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import outline as ol   # noqa: E402
import raster as rs    # noqa: E402
import svgpath as sp   # noqa: E402

WEIGHTS = ("thin", "light", "regular", "bold", "fill", "duotone")
STROKE = {"thin": 8.0, "light": 12.0, "regular": 16.0, "bold": 24.0, "fill": 16.0, "duotone": 16.0}
TINT = 0.2
ASSETS = os.path.join(os.path.dirname(HERE), "assets")

FILL_MODES = ("solid", "knockout", "hole", "none", "plate")
DUO_MODES = ("tint", "plate", "none")
INHERITED = ("fill", "stroke", "fill-rule", "data-fill", "data-duotone", "data-only", "data-not",
             "data-erase", "data-gap", "data-paint")
SHAPES = ("line", "polyline", "polygon", "circle", "ellipse", "rect", "path")


class SourceError(Exception):
    pass


class Element(object):
    def __init__(self):
        self.tag = ""
        self.label = ""
        self.subpaths = []
        self.filled = False
        self.stroked = True
        self.evenodd = False
        self.fill_mode = None
        self.duo_mode = None
        self.only = None
        self.hide = set()
        self.erase = 0.0
        self.gap = 0.0
        self.knockout = False

    def visible(self, weight):
        if self.only is not None and weight not in self.only:
            return False
        if weight in self.hide:
            return False
        plates = set()
        if self.fill_mode == "plate":
            plates.add("fill")
        if self.duo_mode == "plate":
            plates.add("duotone")
        if plates and weight not in plates:
            return False
        if weight == "fill" and self.fill_mode == "none":
            return False
        if weight == "duotone" and self.duo_mode == "none":
            return False
        return True


class Icon(object):
    def __init__(self, name):
        self.name = name
        self.elements = []
        self.notes = []     # (level, message) found while loading
        self.soft = set()   # centres of arcs that stand in for bezier curves


# ---------------------------------------------------------------- loading a source

def _local(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag


def _num(node, key, default=0.0):
    v = node.get(key)
    if v is None or v == "":
        return default
    try:
        return float(re.sub(r"[a-z%]+$", "", v.strip()))
    except ValueError:
        raise SourceError("<%s> has a non-numeric %s=%r" % (_local(node.tag), key, v))


def _weights(text, where):
    out = set()
    for w in re.split(r"[\s,]+", text.strip()):
        if not w:
            continue
        if w not in WEIGHTS:
            raise SourceError("%s names an unknown weight %r (use: %s)" % (where, w, " ".join(WEIGHTS)))
        out.add(w)
    return out


def _style(node):
    out = {}
    for part in (node.get("style") or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def load(path):
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        raise SourceError("%s is not well-formed XML: %s" % (path, e))
    if _local(root.tag) != "svg":
        raise SourceError("%s: root element must be <svg>" % path)
    stem = os.path.basename(path)
    stem = re.sub(r"(\.source)?\.svg$", "", stem)
    name = re.sub(r"[^a-z0-9]+", "-", (root.get("data-name") or stem).lower()).strip("-")
    icon = Icon(name)
    vb = re.split(r"[\s,]+", (root.get("viewBox") or "").strip())
    if vb != ["0", "0", "256", "256"]:
        icon.notes.append(("error", 'viewBox must be "0 0 256 256" (found %r)' % root.get("viewBox")))
    ids = dict((n.get("id"), n) for n in root.iter() if n.get("id"))
    count = [0]

    def walk(node, ctx, matrix, via_use=False):
        tag = _local(node.tag)
        if tag in ("title", "desc", "defs", "metadata", "style"):
            return
        ctx = dict(ctx)
        style = _style(node)
        for key in INHERITED:
            v = node.get(key, style.get(key))
            if via_use and key in ("data-fill", "data-duotone", "data-only", "data-not"):
                v = None    # the <use> decides when a copy shows, not the original
            if v is not None:
                ctx[key] = v
        m = sp.mat_mul(matrix, sp.parse_transform(node.get("transform")))
        if tag in ("svg", "g"):
            for child in node:
                walk(child, ctx, m)
            return
        if tag == "use":
            ref = node.get("href") or node.get("{http://www.w3.org/1999/xlink}href") or ""
            target = ids.get(ref.lstrip("#"))
            if target is None:
                raise SourceError("<use> points at %r, which does not exist" % ref)
            m = sp.mat_mul(m, (1, 0, 0, 1, _num(node, "x"), _num(node, "y")))
            walk(target, ctx, m, via_use=True)
            return
        if tag not in SHAPES:
            icon.notes.append(("warn", "<%s> is not a shape IconKit understands; ignored" % tag))
            return
        count[0] += 1
        el = Element()
        el.tag = tag
        el.label = "#%d <%s%s>" % (count[0], tag, (" id=%s" % node.get("id")) if node.get("id") else "")
        if tag == "line":
            pts = [(_num(node, "x1"), _num(node, "y1")), (_num(node, "x2"), _num(node, "y2"))]
            if pts[0] == pts[1]:
                raise SourceError('%s has no length. For a dot write <circle cx=".." cy=".." r="4" '
                                  'fill="currentColor"/>' % el.label)
            subs = [sp.poly_subpath(pts, False)]
        elif tag in ("polyline", "polygon"):
            nums = [float(v) for v in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", node.get("points") or "")]
            pts = list(zip(nums[0::2], nums[1::2]))
            if len(pts) < 2:
                raise SourceError("%s needs at least two points" % el.label)
            subs = [sp.poly_subpath(pts, tag == "polygon")]
        elif tag == "circle":
            subs = [sp.circle_subpath(_num(node, "cx"), _num(node, "cy"), _num(node, "r"))]
        elif tag == "ellipse":
            subs = [sp.ellipse_subpath(_num(node, "cx"), _num(node, "cy"), _num(node, "rx"), _num(node, "ry"))]
        elif tag == "rect":
            rx = node.get("rx")
            ry = node.get("ry")
            rxv = _num(node, "rx") if rx is not None else (_num(node, "ry") if ry is not None else 0.0)
            ryv = _num(node, "ry") if ry is not None else rxv
            subs = [sp.rect_subpath(_num(node, "x"), _num(node, "y"), _num(node, "width"),
                                    _num(node, "height"), rxv, ryv)]
        else:
            try:
                subs = sp.parse_path(node.get("d") or "")
            except ValueError as e:
                raise SourceError("%s: %s" % (el.label, e))
        el.subpaths = ol.simplify(sp.transform_subpaths(subs, m), 0.02, icon.soft)
        if not el.subpaths:
            icon.notes.append(("warn", "%s draws nothing" % el.label))
            return
        el.filled = ctx.get("fill", "none") not in ("none", "transparent")
        el.stroked = ctx.get("stroke", "currentColor") not in ("none", "transparent")
        el.evenodd = ctx.get("fill-rule") == "evenodd"
        sw = node.get("stroke-width", style.get("stroke-width"))
        if sw is not None and abs(float(sw) - 16) > 1e-6:
            icon.notes.append(("warn", "%s sets stroke-width=%s; ignored - every stroke in a weight has "
                                       "the same width" % (el.label, sw)))
        fm = ctx.get("data-fill")
        if fm is not None:
            if fm not in FILL_MODES:
                raise SourceError("%s: data-fill=%r is not one of %s" % (el.label, fm, ", ".join(FILL_MODES)))
            el.fill_mode = fm
        dm = ctx.get("data-duotone")
        if dm is not None:
            if dm not in DUO_MODES:
                raise SourceError("%s: data-duotone=%r is not one of %s" % (el.label, dm, ", ".join(DUO_MODES)))
            el.duo_mode = dm
        if ctx.get("data-only"):
            el.only = _weights(ctx["data-only"], el.label + " data-only")
        if ctx.get("data-not"):
            el.hide = _weights(ctx["data-not"], el.label + " data-not")
        if ctx.get("data-erase"):
            el.erase = float(ctx["data-erase"])
        if ctx.get("data-gap"):
            el.gap = float(ctx["data-gap"])
            if any(sg[0] != "L" for segs, _ in el.subpaths for sg in segs):
                icon.notes.append(("warn", "%s: data-gap only follows straight segments; curves are skipped"
                                   % el.label))
        paint = ctx.get("data-paint")
        if paint not in (None, "knockout"):
            raise SourceError('%s: data-paint=%r - the only value is "knockout"' % (el.label, paint))
        el.knockout = paint == "knockout"
        if not el.filled and not el.stroked and el.fill_mode not in ("solid", "plate", "hole") \
                and el.duo_mode not in ("tint", "plate"):
            icon.notes.append(("warn", "%s has neither fill nor stroke; ignored" % el.label))
            return
        icon.elements.append(el)

    walk(root, {}, sp.IDENT)
    if not icon.elements:
        raise SourceError("%s contains no shapes" % path)
    return icon


# ---------------------------------------------------------------- building weights

def layers(icon, weight):
    """Paint operations for one weight: (main layer, duotone tint layer)."""
    hw = STROKE[weight] / 2.0
    ops, tint = [], []
    for el in icon.elements:
        if not el.visible(weight):
            continue
        if weight == "duotone" and el.duo_mode in ("tint", "plate"):
            tint.append(ol.Op(el.subpaths, 0.0, True, False, el.evenodd))
            if el.duo_mode == "plate":
                continue
        filled, erase = el.filled, el.knockout
        if weight == "fill" and el.fill_mode in ("solid", "plate"):
            filled, erase = True, False
        elif weight == "fill" and el.fill_mode == "knockout":
            erase = True
        width = hw if el.stroked else 0.0
        if weight == "fill" and el.fill_mode == "hole":
            # the interior of the shape, measured at its centreline, becomes empty
            ops.append(ol.Op(el.subpaths, 0.0, True, True, el.evenodd))
            continue
        if el.erase > 0 and not erase:
            ops.append(ol.Op(el.subpaths, width + el.erase, filled, True, el.evenodd))
        if el.gap and not erase:
            band = _gap_band(el, abs(el.gap) - hw, 1.0 if el.gap > 0 else -1.0)
            if band:
                ops.append(ol.Op(band, (abs(el.gap) - hw) / 2.0, False, True))
        ops.append(ol.Op(el.subpaths, width, filled, erase, el.evenodd))
    return ops, tint


def _gap_band(el, depth, side):
    """Centrelines of the strip to clear beside a slash: `depth` wide, on one side only.

    Phosphor's -slash icons keep the base drawing right up to the slash on one side and
    hold it 32 skeleton units away on the other; the strip between is what we erase.
    """
    if depth <= 0.5:
        return []
    h = depth / 2.0
    band = []
    for segs, _ in el.subpaths:
        for sg in segs:
            if sg[0] != "L":
                continue
            dx, dy = sg[3] - sg[1], sg[4] - sg[2]
            ln = math.hypot(dx, dy)
            if ln <= 2 * h + 1:
                continue
            ux, uy = dx / ln, dy / ln
            nx, ny = uy * side, -ux * side
            band.append(([("L", sg[1] + nx * h + ux * h, sg[2] + ny * h + uy * h,
                           sg[3] + nx * h - ux * h, sg[4] + ny * h - uy * h)], False))
    return band


def build(icon):
    """{weight: [(subpaths, opacity or None), ...]} for all six weights."""
    out = {}
    for w in WEIGHTS:
        ops, tint = layers(icon, w)
        del ol.DROPPED[:]
        parts = []
        if tint:
            parts.append((ol.outline(tint, icon.soft), TINT))
        parts.append((ol.outline(ops, icon.soft), None))
        if ol.DROPPED:
            icon.notes.append(("warn", "%s: %d outline fragment(s) could not be closed and were left out; "
                                       "look for strokes that almost-but-not-quite meet" % (w, len(ol.DROPPED))))
        out[w] = parts
    return out


def svg_text(parts):
    body = "".join('<path d="%s"%s/>' % (sp.to_d(subs), (' opacity="%s"' % sp.fmt(op)) if op else "")
                   for subs, op in parts if subs)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor">%s</svg>\n' % body)


def file_name(name, weight):
    return "%s.svg" % name if weight == "regular" else "%s-%s.svg" % (name, weight)


def pascal(name):
    return "".join(p[:1].upper() + p[1:] for p in name.split("-") if p)


def react_text(name, built):
    comp = pascal(name)
    rows = []
    for w in WEIGHTS:
        paths = "".join('<path d="%s"%s />' % (sp.to_d(subs), (' opacity="%s"' % sp.fmt(op)) if op else "")
                        for subs, op in built[w] if subs)
        rows.append('  ["%s", <>%s</>],' % (w, paths))
    return ('import { forwardRef, type ReactElement } from "react";\n'
            'import { IconBase, type Icon, type IconWeight } from "@phosphor-icons/react";\n\n'
            "// Generated by IconKit from %s.source.svg. Edit the source and rebuild; do not edit this file.\n"
            "const weights = new Map<IconWeight, ReactElement>([\n%s\n]);\n\n"
            "export const %s: Icon = forwardRef((props, ref) => (\n"
            "  <IconBase ref={ref} {...props} weights={weights} />\n));\n\n"
            '%s.displayName = "%s";\n' % (name, "\n".join(rows), comp, comp, comp))


# ---------------------------------------------------------------- the Phosphor reference set

_REF = {}


def phosphor():
    if not _REF:
        path = os.path.join(ASSETS, "phosphor.json.gz")
        with gzip.open(path, "rb") as f:
            _REF.update(json.loads(f.read().decode("utf-8"))["icons"])
    return _REF


def phosphor_parts(name, weight):
    icons = phosphor()
    if name not in icons:
        raise SourceError("Phosphor has no icon called %r (try: iconkit.py find %s)" % (name, name))
    return [(sp.parse_path(p[0]), p[1] if len(p) > 1 else None) for p in icons[name][weight]]


SYNONYMS = {
    "settings": "gear sliders faders wrench", "config": "gear sliders faders wrench", "preferences": "gear sliders",
    "search": "magnifying-glass binoculars", "find": "magnifying-glass binoculars", "lookup": "magnifying-glass",
    "delete": "trash x eraser backspace", "remove": "trash minus x", "edit": "pencil pen note-pencil",
    "write": "pencil pen note-pencil", "ai": "sparkle robot brain magic-wand open-ai-logo head-circuit",
    "ml": "brain robot graph head-circuit", "magic": "sparkle magic-wand", "generate": "sparkle magic-wand lightning",
    "notification": "bell", "alert": "bell warning siren megaphone", "home": "house", "profile": "user identification",
    "account": "user identification-card", "person": "user", "people": "users", "team": "users users-three users-four",
    "group": "users circles-three selection", "security": "shield lock key fingerprint", "secure": "shield lock",
    "permission": "key lock shield user-gear", "access": "key lock door", "auth": "key lock fingerprint password sign-in",
    "login": "sign-in key", "logout": "sign-out", "password": "password key lock", "secret": "key eye-slash lock detective",
    "time": "clock timer hourglass watch alarm", "schedule": "calendar clock", "date": "calendar", "history": "clock-counter-clockwise",
    "money": "currency coin coins bank wallet money", "billing": "credit-card receipt invoice", "payment": "credit-card wallet",
    "price": "tag currency", "api": "plugs brackets-curly code webhooks-logo", "integration": "plugs plugs-connected puzzle-piece",
    "plugin": "puzzle-piece plug", "extension": "puzzle-piece", "webhook": "webhooks-logo", "data": "database chart table",
    "storage": "database hard-drive", "filter": "funnel sliders", "sort": "sort arrows-down-up", "workflow": "flow-arrow tree-structure git-branch",
    "pipeline": "flow-arrow pipe git-branch", "automation": "robot lightning gear flow-arrow", "version": "git-branch git-commit clock-counter-clockwise",
    "branch": "git-branch tree", "merge": "git-merge arrows-merge", "sync": "arrows-clockwise cloud-check", "refresh": "arrows-clockwise arrow-clockwise",
    "upload": "upload cloud-arrow-up export", "download": "download cloud-arrow-down", "share": "share export", "link": "link",
    "docs": "file-text book article notebook", "document": "file file-text article", "analytics": "chart-line chart-bar trend-up",
    "report": "chart-bar file-text presentation", "dashboard": "squares-four gauge layout", "metrics": "chart gauge pulse",
    "email": "envelope at", "mail": "envelope mailbox", "message": "chat envelope", "chat": "chat chats", "comment": "chat",
    "label": "tag", "test": "flask test-tube bug check", "debug": "bug", "deploy": "rocket rocket-launch cloud-arrow-up",
    "release": "rocket package tag", "environment": "stack globe cube", "monitor": "pulse monitor gauge", "health": "heartbeat pulse",
    "speed": "gauge speedometer lightning", "limit": "gauge speedometer hourglass prohibit", "rate": "gauge speedometer",
    "throttle": "gauge speedometer", "performance": "gauge speedometer lightning", "schema": "tree-structure brackets-curly table",
    "graph": "graph share-network tree-structure", "network": "network share-network graph globe", "knowledge": "brain book lightbulb",
    "idea": "lightbulb", "learn": "graduation-cap book", "error": "warning x-circle bug", "success": "check check-circle",
    "info": "info question", "help": "question lifebuoy", "support": "lifebuoy headset", "image": "image", "photo": "image camera",
    "video": "video play", "audio": "speaker microphone waveform", "folder": "folder", "file": "file", "copy": "copy",
    "paste": "clipboard", "save": "floppy-disk", "print": "printer", "location": "map-pin", "map": "map-trifold map-pin",
    "world": "globe", "language": "translate globe", "code": "code brackets-curly terminal", "terminal": "terminal",
    "server": "hard-drives database cloud", "cloud": "cloud", "compute": "cpu", "layers": "stack", "template": "layout squares-four",
    "component": "puzzle-piece cube", "module": "cube package", "package": "package cube", "favorite": "star heart", "like": "heart thumbs-up",
    "visible": "eye", "hide": "eye-slash", "lock": "lock", "unlock": "lock-open", "expand": "arrows-out", "collapse": "arrows-in",
    "menu": "list dots-three", "more": "dots-three", "add": "plus", "new": "plus", "close": "x", "approve": "check seal-check",
    "review": "eye check magnifying-glass", "audit": "list-checks clipboard-text magnifying-glass", "log": "list scroll terminal",
    "queue": "queue list stack", "cache": "lightning database", "token": "coin key", "role": "user-gear identification-badge",
    "tenant": "buildings", "organization": "buildings building-office", "company": "buildings", "trigger": "lightning play",
    "event": "lightning calendar", "experiment": "flask test-tube", "feature": "flag toggle-right puzzle-piece", "flag": "flag",
    "toggle": "toggle-left toggle-right", "import": "download-simple sign-in", "export": "export upload-simple", "scan": "scan barcode qr-code",
    "target": "target crosshair", "goal": "target flag", "compare": "git-diff arrows-left-right", "diff": "git-diff", "route": "path signpost",
    "gateway": "door plugs", "proxy": "arrows-left-right swap", "prompt": "terminal chat-text", "agent": "robot user-gear", "bot": "robot",
    "vector": "bezier-curve vector-two", "embedding": "vector-three graph", "model": "cube brain", "tool": "wrench hammer toolbox",
}


def find(words, limit=18):
    names = sorted(phosphor())
    terms = []
    for w in words:
        for t in re.split(r"[^a-z0-9]+", w.lower()):
            if t:
                terms.append(t)
    wanted = {}
    for t in terms:
        wanted[t] = max(wanted.get(t, 0), 3.0)
        stem = re.sub(r"(ing|ed|es|s)$", "", t)
        if len(stem) >= 3:
            wanted[stem] = max(wanted.get(stem, 0), 2.5)
        for syn in SYNONYMS.get(t, "").split() + SYNONYMS.get(stem, "").split():
            for part in [syn] + syn.split("-"):
                wanted[part] = max(wanted.get(part, 0), 1.5 if part == syn else 1.0)
    scored = []
    for n in names:
        parts = n.split("-")
        score = 0.0
        for t, wgt in wanted.items():
            if t == n:
                score += wgt * 3
            elif t in parts:
                score += wgt * 2
            elif any(p.startswith(t) for p in parts) and len(t) >= 3:
                score += wgt
            elif len(t) >= 4 and t in n:
                score += wgt * 0.5
        if score:
            scored.append((score - 0.05 * len(parts), n))
    scored.sort(key=lambda sn: (-sn[0], sn[1]))
    return [n for _, n in scored[:limit]]


# ---------------------------------------------------------------- previews

GUIDE = (228, 232, 240)
GUIDE2 = (196, 214, 245)
INK = (17, 17, 17)
LABEL = (110, 114, 122)
ACCENT = (232, 90, 60)


def _draw(canvas, parts, x, y, size, color=INK):
    s = size / 256.0
    for subs, op in parts:
        if subs:
            canvas.fill(subs, color, op if op else 1.0, s, x, y)


def _guides(canvas, x, y, size):
    s = size / 256.0
    canvas.frame(int(x), int(y), int(size), int(size), GUIDE)
    m = int(round(24 * s))
    canvas.frame(int(x) + m, int(y) + m, int(size) - 2 * m, int(size) - 2 * m, GUIDE2)


def render_sheet(rows, path, cell=132, guides=True):
    """rows: [(label, {weight: parts})] -> six-weight contact sheet."""
    left = 12 + max(rs.text_width(r[0]) for r in rows) + 16
    pad = 12
    w = left + len(WEIGHTS) * (cell + pad) + 4
    h = 34 + len(rows) * (cell + pad) + 4
    c = rs.Canvas(w, h)
    for j, wt in enumerate(WEIGHTS):
        c.text(left + j * (cell + pad) + (cell - rs.text_width(wt)) // 2, 12, wt, LABEL)
    for i, (label, built) in enumerate(rows):
        y = 34 + i * (cell + pad)
        c.text(12, y + cell // 2 - 7, label, INK)
        for j, wt in enumerate(WEIGHTS):
            x = left + j * (cell + pad)
            if guides:
                _guides(c, x, y, cell)
            _draw(c, built[wt], x, y, cell)
    c.save(path)
    return w, h


def render_preview(name, built, neighbours, path):
    """One image that answers: is it right, does it survive small sizes, does it belong?"""
    big, gap, m = 160, 12, 24
    width = m * 2 + 6 * big + 5 * gap
    lane = (width - 2 * m) // 2
    sizes = (16, 20, 24, 32)
    zoom = 4
    small_h = max(sizes) * zoom
    line = 48
    height = m + 30 + big + 44 + 30 + 2 * (22 + small_h + 30) + 34 + 2 * (22 + line + 30) + m
    c = rs.Canvas(width, height)
    y = m
    x = c.text(m, y, name, INK, 2)
    c.text(x + 18, y, "256 grid, blue box = 24 unit margin", LABEL, 2)
    y += 30
    for j, wt in enumerate(WEIGHTS):
        x = m + j * (big + gap)
        _guides(c, x, y, big)
        _draw(c, built[wt], x, y, big)
        c.text(x + (big - rs.text_width(wt)) // 2, y + big + 10, wt, LABEL)
    y += big + 44

    # true pixel sizes, enlarged with hard pixels so blur and clogging are visible
    c.text(m, y, "actual pixels, enlarged x%d" % zoom, INK, 2)
    y += 30
    for pair in (("regular", "fill"), ("bold", "duotone")):
        for col, wt in enumerate(pair):
            x = m + col * lane
            c.text(x, y, wt, LABEL)
            for s in sizes:
                tile = rs.Canvas(s, s)
                _draw(tile, built[wt], 0, 0, s)
                c.blit_scaled(tile, x, y + 22 + small_h - s * zoom, zoom)
                c.text(x, y + 22 + small_h + 8, "%dpx" % s, LABEL)
                x += s * zoom + 20
        y += 22 + small_h + 30

    # in a row with real Phosphor icons: same optical size? same weight?
    c.text(m, y, "in a row with real phosphor icons (yours is underlined)", INK, 2)
    y += 34
    half = len(neighbours) // 2
    for pair in (("regular", "fill"), ("bold", "duotone")):
        for col, wt in enumerate(pair):
            x = m + col * lane
            c.text(x, y, wt, LABEL)
            seq = [(n, phosphor_parts(n, wt)) for n in neighbours[:half]] + [(None, built[wt])] \
                + [(n, phosphor_parts(n, wt)) for n in neighbours[half:]]
            for n, parts in seq:
                _draw(c, parts, x, y + 22, line)
                if n is None:
                    c.rect(x + 8, y + 22 + line + 6, line - 16, 3, ACCENT)
                x += line + 14
        y += 22 + line + 30
    c.save(path)
    return width, height


# ---------------------------------------------------------------- checks

def _area(pts):
    a = 0.0
    for i in range(len(pts) - 1):
        a += pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1]
    return a / 2.0


def _stats(parts):
    """bbox, ink area, contour count, hole list for one built weight (solid layer only)."""
    subs = [s for sub, op in parts if op is None for s in sub]
    box = sp.bbox(subs)
    loops = []
    for pts, sub in zip(sp.flatten(subs, 0.02), subs):
        loops.append((_area(pts), pts))
    if not loops:
        return None
    outer_sign = 1 if max(loops, key=lambda l: abs(l[0]))[0] > 0 else -1
    ink = sum(a for a, _ in loops) * outer_sign
    holes = []
    for a, pts in loops:
        if a * outer_sign < 0:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            holes.append((abs(a), (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2,
                          min(max(xs) - min(xs), max(ys) - min(ys))))
    return {"box": box, "ink": ink, "loops": len(loops), "holes": holes,
            "bodies": len(loops) - len(holes)}


def check(icon, built):
    """Return [(level, message)] - level is error, warn or note."""
    out = list(icon.notes)
    st = dict((w, _stats(built[w])) for w in WEIGHTS)
    if st["regular"] is None:
        return out + [("error", "the regular weight is empty")]
    x0, y0, x1, y1 = st["regular"]["box"]
    w, h = x1 - x0, y1 - y0

    # --- the canvas (thresholds are measured from Phosphor itself; see SPEC.md)
    bold = st["bold"]["box"] if st["bold"] else st["regular"]["box"]
    if min(bold[0], bold[1]) < -0.01 or max(bold[2], bold[3]) > 256.01:
        out.append(("error", "bold weight leaves the 256 canvas (%.0f,%.0f - %.0f,%.0f) and will be clipped"
                    % bold))
    if min(x0, y0) < 7.99 or max(x1, y1) > 248.01:
        out.append(("warn", "regular ink spans %.0f..%.0f x %.0f..%.0f. Fewer than 1 in 10 Phosphor icons pass "
                            "8..248; pull the skeleton inside 24..232" % (x0, x1, y0, y1)))
    elif min(x0, y0) < 15.99 or max(x1, y1) > 240.01:
        out.append(("note", "regular ink spans %.0f..%.0f x %.0f..%.0f. Past 16..240 is normal only for a "
                            "subject that is long in one direction; the usual skeleton box is 32..224"
                    % (x0, x1, y0, y1)))
    longest = max(w, h)
    if longest < 175.9:
        out.append(("warn", "icon is small: %.0f units of ink on its long side. 95%% of Phosphor icons reach "
                            "176+, and the usual is 208 (skeleton 192). Scale it up" % longest))
    if min(w, h) < 95.9 and len(icon.elements) > 1:
        out.append(("note", "short side is only %.0f units; fine for a deliberately flat or thin subject" % min(w, h)))
    dx, dy = (x0 + x1) / 2 - 128, (y0 + y1) / 2 - 128
    if abs(dx) > 12.01:
        out.append(("warn", "sits %.0f units %s of centre; 3 in 4 Phosphor icons are centred exactly and 95%% "
                            "are within 12" % (abs(dx), "right" if dx > 0 else "left")))
    if abs(dy) > 12.01:
        out.append(("warn", "sits %.0f units %s centre; 95%% of Phosphor icons are within 12"
                    % (abs(dy), "below" if dy > 0 else "above")))

    # --- the grid
    off = 0
    total = 0
    for el in icon.elements:
        for segs, _ in el.subpaths:
            for s in segs:
                for v in (sp.seg_start(s) + sp.seg_end(s)):
                    total += 1
                    if abs(v - round(v)) > 0.02:
                        off += 1
    if total and off > total * 0.5:
        out.append(("note", "%d of %d skeleton coordinates are off the whole-unit grid. Phosphor draws on "
                            "multiples of 8 (4 for small details); diagonals and curves are the usual exception"
                    % (off, total)))

    # --- does every weight keep its shape?
    reg = st["regular"]
    for wt in ("thin", "light", "bold"):
        s = st[wt]
        if s is None:
            out.append(("error", "%s weight is empty" % wt))
            continue
        if len(s["holes"]) < len(reg["holes"]):
            out.append(("warn" if wt == "bold" else "note",
                        "%s has %d counter(s), regular has %d: an opening closes up as strokes thicken. "
                        "Parallel strokes need centrelines 32+ apart (28 at the very least)"
                        % (wt, len(s["holes"]), len(reg["holes"]))))
        elif s["bodies"] < reg["bodies"] and wt == "bold":
            out.append(("warn", "bold merges parts that are separate in regular (%d -> %d). Separate parts need "
                                "32+ between centrelines" % (reg["bodies"], s["bodies"])))
    if st["bold"]:
        for a, cx, cy, thin_side in st["bold"]["holes"]:
            if thin_side < 11.99:
                out.append(("warn", "bold: the opening at (%.0f, %.0f) is only %.1f units across and will clog; "
                                    "Phosphor keeps bold openings at 12+ (usually 16+)" % (cx, cy, thin_side)))
    for a, cx, cy, thin_side in reg["holes"]:
        if thin_side < 15.99:
            out.append(("warn", "regular: the opening at (%.0f, %.0f) is %.1f units across - under one pixel "
                                "at 16 px. Phosphor never goes below 16; simplify or enlarge it" % (cx, cy, thin_side)))

    # --- fill and duotone are designed, not derived
    modes = [el.fill_mode for el in icon.elements]
    if not any(m in ("solid", "plate") for m in modes):
        out.append(("error", 'fill weight has nothing solid. Mark the main body data-fill="solid", or give an '
                             'open glyph a data-fill="plate" container (see references/weights.md)'))
    elif st["fill"] and st["fill"]["ink"] < reg["ink"] * 1.1:
        out.append(("note", "fill weight carries barely more ink than regular (x%.2f; Phosphor's median is x1.8). "
                            "Fine for an arrow-like glyph, thin for anything with a body"
                    % (st["fill"]["ink"] / reg["ink"])))
    if st["fill"]:
        for a, cx, cy, thin_side in st["fill"]["holes"]:
            if thin_side < 15.99:
                out.append(("warn", "fill: the knocked-out detail at (%.0f, %.0f) is %.1f units across; knockouts "
                                    "need the full 16 unit line (dots r=12) to survive" % (cx, cy, thin_side)))
    if not any(el.duo_mode in ("tint", "plate") for el in icon.elements):
        out.append(("error", 'duotone has no tint. Mark one closed body data-duotone="tint", or add a '
                             'data-duotone="plate" backing shape for an open glyph'))

    # --- paint order: later elements cover earlier ones
    fill_els = [el for el in icon.elements if el.visible("fill")]
    for i, el in enumerate(fill_els):
        if el.fill_mode not in ("knockout", "hole"):
            continue
        a = sp.bbox(el.subpaths)
        for later in fill_els[i + 1:]:
            if later.fill_mode in ("solid", "plate"):
                b = sp.bbox(later.subpaths)
                if a[0] >= b[0] - 8 and a[1] >= b[1] - 8 and a[2] <= b[2] + 8 and a[3] <= b[3] + 8:
                    out.append(("error", "%s is knocked out of the fill weight, but %s comes after it and "
                                         "paints over the cut. Elements paint in order: move the knockout "
                                         "below the solid it cuts" % (el.label, later.label)))
                    break

    if icon.name in phosphor():
        out.append(("warn", "Phosphor already has an icon named %r; pick a name that says how yours differs"
                    % icon.name))

    # --- restraint
    visible = [el for el in icon.elements if el.visible("regular")]
    if len(visible) > 9:
        out.append(("warn", "regular weight uses %d elements; most Phosphor icons need 2-6. Cut detail that "
                            "will not survive at 16 px" % len(visible)))
    ink_pct = 100.0 * reg["ink"] / 65536
    if ink_pct < INK_RANGE[0]:
        out.append(("note", "regular ink covers %.1f%% of the canvas; Phosphor's middle 90%% is %.0f-%.0f%%. "
                            "It may look light next to its neighbours" % ((ink_pct,) + INK_RANGE)))
    elif ink_pct > INK_RANGE[1]:
        out.append(("note", "regular ink covers %.1f%% of the canvas; Phosphor's middle 90%% is %.0f-%.0f%%. "
                            "It may look heavy or busy next to its neighbours" % ((ink_pct,) + INK_RANGE)))
    return out


INK_RANGE = (10.0, 27.0)  # regular-weight ink coverage, 5th..95th percentile of Phosphor (measured)


# ---------------------------------------------------------------- commands

def _report(notes):
    order = {"error": 0, "warn": 1, "note": 2}
    notes = sorted(set(notes), key=lambda n: order[n[0]])
    for level, msg in notes:
        print("  %-5s %s" % (level.upper(), msg))
    errors = sum(1 for n in notes if n[0] == "error")
    warns = sum(1 for n in notes if n[0] == "warn")
    return errors, warns


def cmd_build(args):
    icon = load(args.source)
    if args.name:
        icon.name = args.name
    built = build(icon)
    notes = check(icon, built)
    folder = os.path.dirname(os.path.abspath(args.source))
    out = args.out or (folder if os.path.basename(folder) == icon.name else os.path.join(folder, icon.name))
    if not os.path.isdir(out):
        os.makedirs(out)
    for w in WEIGHTS:
        with open(os.path.join(out, file_name(icon.name, w)), "w") as f:
            f.write(svg_text(built[w]))
    if args.react:
        with open(os.path.join(out, pascal(icon.name) + ".tsx"), "w") as f:
            f.write(react_text(icon.name, built))
    neighbours = [n.strip() for n in (args.near or "house,gear,user,bell,lock,magnifying-glass").split(",") if n.strip()]
    for n in neighbours:
        if n not in phosphor():
            raise SourceError("--near: Phosphor has no icon called %r" % n)
    render_preview(icon.name, built, neighbours, os.path.join(out, "preview.png"))
    print("%s -> %s" % (icon.name, out))
    print("  wrote %s%s, preview.png" % (", ".join(file_name(icon.name, w) for w in WEIGHTS),
                                         (", %s.tsx" % pascal(icon.name)) if args.react else ""))
    errors, warns = _report(notes)
    if not notes:
        print("  checks: clean")
    print("  now LOOK at %s before calling it done" % os.path.join(out, "preview.png"))
    return 1 if errors else 0


def cmd_check(args):
    icon = load(args.source)
    notes = check(icon, build(icon))
    print(icon.name)
    errors, warns = _report(notes)
    if not notes:
        print("  checks: clean")
    return 1 if errors else 0


def cmd_find(args):
    hits = find(args.words, args.limit)
    if not hits:
        print("no Phosphor icon matches %r - try other words for the same idea" % " ".join(args.words))
        return 0
    print("Phosphor icons matching %r (best first):" % " ".join(args.words))
    for n in hits:
        print("  " + n)
    print("look at them:  iconkit.py sheet %s -o /tmp/refs.png" % " ".join(hits[:6]))
    return 0


def cmd_sheet(args):
    rows = []
    for n in args.names:
        if n.endswith(".svg"):
            icon = load(n)
            rows.append((icon.name, build(icon)))
        else:
            rows.append((n, dict((w, phosphor_parts(n, w)) for w in WEIGHTS)))
    w, h = render_sheet(rows, args.out, guides=not args.plain)
    print("wrote %s (%dx%d): %s" % (args.out, w, h, ", ".join(r[0] for r in rows)))
    return 0


def cmd_show(args):
    icons = phosphor()
    if args.name not in icons:
        raise SourceError("Phosphor has no icon called %r" % args.name)
    for w in ([args.weight] if args.weight else WEIGHTS):
        parts = phosphor_parts(args.name, w)
        box = sp.bbox([s for subs, op in parts if op is None for s in subs])
        print("%s  ink %.0f..%.0f x %.0f..%.0f" % ((w,) + (box[0], box[2], box[1], box[3])))
        for p in icons[args.name][w]:
            print("  %s%s" % (p[0], "   (opacity %s)" % p[1] if len(p) > 1 else ""))
    return 0


def _coverage(parts_a, parts_b, size=128):
    a = rs.Canvas(size, size)
    b = rs.Canvas(size, size)
    _draw(a, parts_a, 0, 0, size, (0, 0, 0))
    _draw(b, parts_b, 0, 0, size, (0, 0, 0))
    diff = ink = 0
    for i in range(0, len(a.px), 3):
        diff += abs(a.px[i] - b.px[i])
        ink += 255 - b.px[i]
    return 100.0 * diff / max(ink, 1)


def cmd_compare(args):
    icon = load(args.source)
    built = build(icon)
    print("%s vs phosphor:%s  (ink that differs, as %% of the real icon's ink)" % (icon.name, args.name))
    worst = 0.0
    for w in WEIGHTS:
        d = _coverage(built[w], phosphor_parts(args.name, w))
        worst = max(worst, d)
        print("  %-8s %6.2f%%" % (w, d))
    if args.out:
        rows = [(icon.name, built), (args.name, dict((w, phosphor_parts(args.name, w)) for w in WEIGHTS))]
        render_sheet(rows, args.out)
        print("wrote %s" % args.out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="iconkit.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("build", help="build all six weights and a preview from a skeleton source")
    p.add_argument("source")
    p.add_argument("-o", "--out", help="output folder (default: next to the source, in a folder named after the icon)")
    p.add_argument("--name", help="icon name in kebab-case (default: from the source)")
    p.add_argument("--near", help="six comma-separated Phosphor icons to line up against in the preview")
    p.add_argument("--react", action="store_true", help="also write a @phosphor-icons/react component")
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("check", help="lint a skeleton source")
    p.add_argument("source")
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser("find", help="search the 1,512 Phosphor icons by idea")
    p.add_argument("words", nargs="+")
    p.add_argument("--limit", type=int, default=18)
    p.set_defaults(fn=cmd_find)
    p = sub.add_parser("sheet", help="render Phosphor icons (or sources) in all six weights")
    p.add_argument("names", nargs="+", help="Phosphor names, or paths to .svg sources")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--plain", action="store_true", help="no guide boxes")
    p.set_defaults(fn=cmd_sheet)
    p = sub.add_parser("show", help="print a Phosphor icon's outlined path data")
    p.add_argument("name")
    p.add_argument("weight", nargs="?", choices=WEIGHTS)
    p.set_defaults(fn=cmd_show)
    p = sub.add_parser("compare", help="measure a source against a real Phosphor icon")
    p.add_argument("source")
    p.add_argument("name")
    p.add_argument("-o", "--out", help="write a side-by-side sheet")
    p.set_defaults(fn=cmd_compare)
    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 2
    try:
        return args.fn(args)
    except SourceError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
