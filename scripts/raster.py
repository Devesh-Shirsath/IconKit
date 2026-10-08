"""A small anti-aliased rasteriser and PNG writer, so previews need no dependencies.

Fills flattened paths with the non-zero rule: several sub-scanlines per pixel row,
exact coverage horizontally. Good enough to judge an icon at 16 px.

Standard library only.
"""
import math
import struct
import zlib

from svgpath import flatten

SS = 5  # sub-scanlines per pixel row


class Canvas(object):
    def __init__(self, width, height, bg=(255, 255, 255)):
        self.w, self.h = int(width), int(height)
        self.px = bytearray(bytes(bytearray(bg)) * (self.w * self.h))

    # ------------------------------------------------------------ drawing
    def fill(self, subpaths, color=(0, 0, 0), opacity=1.0, scale=1.0, dx=0.0, dy=0.0, tol=None):
        """Fill subpaths (in their own units) placed at (dx, dy) and scaled by `scale`."""
        tol = tol if tol is not None else 0.02 / max(scale, 1e-6)
        polys = flatten(subpaths, tol)
        rows = {}
        for pts in polys:
            if len(pts) < 2:
                continue
            if pts[0] != pts[-1]:
                pts = pts + [pts[0]]
            for i in range(len(pts) - 1):
                x0, y0 = pts[i][0] * scale + dx, pts[i][1] * scale + dy
                x1, y1 = pts[i + 1][0] * scale + dx, pts[i + 1][1] * scale + dy
                if y0 == y1:
                    continue
                d = 1
                if y0 > y1:
                    x0, y0, x1, y1, d = x1, y1, x0, y0, -1
                k0 = int(math.ceil(y0 * SS - 0.5))
                k1 = int(math.ceil(y1 * SS - 0.5))
                if k0 < 0:
                    k0 = 0
                if k1 > self.h * SS:
                    k1 = self.h * SS
                slope = (x1 - x0) / (y1 - y0)
                for k in range(k0, k1):
                    y = (k + 0.5) / SS
                    rows.setdefault(k, []).append((x0 + (y - y0) * slope, d))
        if not rows:
            return
        w, px = self.w, self.px
        wgt = 1.0 / SS
        r, g, b = color
        for row in range(min(rows) // SS, max(rows) // SS + 1):
            if row < 0 or row >= self.h:
                continue
            part = {}
            lo, hi = w, -1
            for k in range(row * SS, row * SS + SS):
                xs = rows.get(k)
                if not xs:
                    continue
                xs.sort()
                wn = 0
                start = 0.0
                for x, d in xs:
                    if wn == 0:
                        start = x
                    wn += d
                    if wn == 0:
                        xa, xb = max(0.0, start), min(float(w), x)
                        if xb <= xa:
                            continue
                        ia, ib = int(xa), int(xb)
                        if ib >= w:
                            ib = w - 1
                        if ia < lo:
                            lo = ia
                        if ib > hi:
                            hi = ib
                        if ia == ib:
                            part[ia] = part.get(ia, 0.0) + (xb - xa) * wgt
                        else:
                            part[ia] = part.get(ia, 0.0) + (ia + 1 - xa) * wgt
                            part[ib] = part.get(ib, 0.0) + (xb - ib) * wgt
                            for i in range(ia + 1, ib):
                                part[i] = part.get(i, 0.0) + wgt
            base = row * w * 3
            for i, cov in part.items():
                a = cov * opacity
                if a <= 0:
                    continue
                if a > 1:
                    a = 1.0
                o = base + i * 3
                px[o] = int(px[o] + (r - px[o]) * a + 0.5)
                px[o + 1] = int(px[o + 1] + (g - px[o + 1]) * a + 0.5)
                px[o + 2] = int(px[o + 2] + (b - px[o + 2]) * a + 0.5)

    def rect(self, x, y, w, h, color):
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(self.w, int(x + w)), min(self.h, int(y + h))
        if x1 <= x0:
            return
        row = bytes(bytearray(color)) * (x1 - x0)
        for yy in range(y0, y1):
            o = (yy * self.w + x0) * 3
            self.px[o:o + len(row)] = row

    def frame(self, x, y, w, h, color):
        self.rect(x, y, w, 1, color)
        self.rect(x, y + h - 1, w, 1, color)
        self.rect(x, y, 1, h, color)
        self.rect(x + w - 1, y, 1, h, color)

    def text(self, x, y, s, color=(90, 90, 90), size=2):
        """Draw text in the built-in 5x7 capitals; `size` is the pixel multiple."""
        cx = int(x)
        for ch in s:
            glyph = FONT.get(ch.upper()) or FONT["?"]
            for ry, bits in enumerate(glyph):
                for rx in range(5):
                    if bits >> (4 - rx) & 1:
                        self.rect(cx + rx * size, int(y) + ry * size, size, size, color)
            cx += 6 * size
        return cx

    def blit_scaled(self, src, x, y, factor):
        """Paste another canvas enlarged by an integer factor with hard pixels."""
        x, y = int(x), int(y)
        for sy in range(src.h):
            line = bytearray()
            o = sy * src.w * 3
            for sx in range(src.w):
                line += src.px[o + sx * 3:o + sx * 3 + 3] * factor
            keep = max(0, min(src.w * factor, self.w - x)) * 3
            if keep <= 0 or x < 0:
                continue
            for k in range(factor):
                yy = y + sy * factor + k
                if 0 <= yy < self.h:
                    d = (yy * self.w + x) * 3
                    self.px[d:d + keep] = line[:keep]

    # ------------------------------------------------------------ output
    def png(self):
        raw = bytearray()
        stride = self.w * 3
        for yy in range(self.h):
            raw.append(0)
            raw += self.px[yy * stride:(yy + 1) * stride]

        def chunk(tag, data):
            body = tag + data
            return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b""))

    def save(self, path):
        with open(path, "wb") as f:
            f.write(self.png())


def text_width(s, size=2):
    return len(s) * 6 * size


def _font():
    rows = {
        "A": ".###. #...# #...# ##### #...# #...# #...#", "B": "####. #...# #...# ####. #...# #...# ####.",
        "C": ".###. #...# #.... #.... #.... #...# .###.", "D": "####. #...# #...# #...# #...# #...# ####.",
        "E": "##### #.... #.... ####. #.... #.... #####", "F": "##### #.... #.... ####. #.... #.... #....",
        "G": ".###. #...# #.... #.### #...# #...# .###.", "H": "#...# #...# #...# ##### #...# #...# #...#",
        "I": ".###. ..#.. ..#.. ..#.. ..#.. ..#.. .###.", "J": "..### ...#. ...#. ...#. ...#. #..#. .##..",
        "K": "#...# #..#. #.#.. ##... #.#.. #..#. #...#", "L": "#.... #.... #.... #.... #.... #.... #####",
        "M": "#...# ##.## #.#.# #.#.# #...# #...# #...#", "N": "#...# ##..# #.#.# #..## #...# #...# #...#",
        "O": ".###. #...# #...# #...# #...# #...# .###.", "P": "####. #...# #...# ####. #.... #.... #....",
        "Q": ".###. #...# #...# #...# #.#.# #..#. .##.#", "R": "####. #...# #...# ####. #.#.. #..#. #...#",
        "S": ".#### #.... #.... .###. ....# ....# ####.", "T": "##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..",
        "U": "#...# #...# #...# #...# #...# #...# .###.", "V": "#...# #...# #...# #...# #...# .#.#. ..#..",
        "W": "#...# #...# #...# #.#.# #.#.# ##.## #...#", "X": "#...# #...# .#.#. ..#.. .#.#. #...# #...#",
        "Y": "#...# #...# .#.#. ..#.. ..#.. ..#.. ..#..", "Z": "##### ....# ...#. ..#.. .#... #.... #####",
        "0": ".###. #...# #..## #.#.# ##..# #...# .###.", "1": "..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.",
        "2": ".###. #...# ....# ...#. ..#.. .#... #####", "3": "##### ...#. ..#.. ...#. ....# #...# .###.",
        "4": "...#. ..##. .#.#. #..#. ##### ...#. ...#.", "5": "##### #.... ####. ....# ....# #...# .###.",
        "6": "..##. .#... #.... ####. #...# #...# .###.", "7": "##### ....# ...#. ..#.. .#... .#... .#...",
        "8": ".###. #...# #...# .###. #...# #...# .###.", "9": ".###. #...# #...# .#### ....# ...#. .##..",
        "-": "..... ..... ..... ##### ..... ..... .....", "_": "..... ..... ..... ..... ..... ..... #####",
        ".": "..... ..... ..... ..... ..... .##.. .##..", ",": "..... ..... ..... ..... .##.. ..#.. .#...",
        ":": "..... .##.. .##.. ..... .##.. .##.. .....", "/": "....# ....# ...#. ..#.. .#... #.... #....",
        "(": "...#. ..#.. .#... .#... .#... ..#.. ...#.", ")": ".#... ..#.. ...#. ...#. ...#. ..#.. .#...",
        "+": "..... ..#.. ..#.. ##### ..#.. ..#.. .....", "=": "..... ..... ##### ..... ##### ..... .....",
        "%": "##..# ##..# ...#. ..#.. .#... #..## #..##", "?": ".###. #...# ....# ...#. ..#.. ..... ..#..",
        " ": "..... ..... ..... ..... ..... ..... .....",
    }
    return dict((ch, [int(r.replace(".", "0").replace("#", "1"), 2) for r in spec.split()])
                for ch, spec in rows.items())


FONT = _font()
