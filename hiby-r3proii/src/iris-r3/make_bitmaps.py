#!/usr/bin/env python3
"""Generate the iris-r3 skin bitmaps (24-bit BMP, no dependencies).

Usage: python3 make_bitmaps.py <device-folder>/.rockbox

Shapes are rasterised with 4x4 supersampling and pre-blended onto the solid
background they sit on, so no transparency is needed. Magenta (FF00FF) is
Rockbox's transparent colour and is only used for the blank iconset.
"""
import math
import os
import struct
import sys

# Rose Pine colours as used by Iris
BG = (0x18, 0x14, 0x20)       # base
OVERLAY = (0x28, 0x24, 0x38)  # status strip, play button
ACCENT = (0xC0, 0xA4, 0xE0)   # iris
TEXT = (0xD8, 0xD8, 0xE8)
DIM = (0x68, 0x68, 0x80)
MAGENTA = (0xFF, 0x00, 0xFF)

SS = 4  # supersampling per axis


def write_bmp(path, width, height, rows):
    """rows: list of height rows, top first, each a list of (r, g, b).

    Writes an 8-bit palette BMP (each image here uses well under 256
    colours), which is a third of the size of 24-bit.
    """
    palette = sorted({px for row in rows for px in row})
    if len(palette) > 256:
        raise ValueError(f"{path}: {len(palette)} colours, more than an 8-bit palette holds")
    index = {colour: i for i, colour in enumerate(palette)}
    stride = (width + 3) & ~3
    data = bytearray()
    for row in reversed(rows):
        line = bytes(index[px] for px in row)
        data += line + b"\0" * (stride - len(line))
    table = b"".join(bytes((b, g, r, 0)) for r, g, b in palette)
    offset = 54 + len(table)
    header = struct.pack("<2sIHHI", b"BM", offset + len(data), 0, 0, offset)
    info = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 8, 0, len(data), 2835, 2835,
                       len(palette), 0) + table
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(header + info + data)


# --- shape tests: each takes (x, y) in icon pixel space and returns bool ---

def circle(cx, cy, r):
    return lambda x, y: (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def rect(x0, y0, x1, y1):
    return lambda x, y: x0 <= x <= x1 and y0 <= y <= y1


def polygon(points):
    def inside(x, y):
        hit = False
        n = len(points)
        for i in range(n):
            (xa, ya), (xb, yb) = points[i], points[(i + 1) % n]
            if (ya > y) != (yb > y) and x < (xb - xa) * (y - ya) / (yb - ya) + xa:
                hit = not hit
        return hit
    return inside


def stroke(points, width):
    """Thick polyline with round joins and caps."""
    half = width / 2

    def seg_dist(px, py, ax, ay, bx, by):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    def inside(x, y):
        return any(seg_dist(x, y, *points[i], *points[i + 1]) <= half for i in range(len(points) - 1))
    return inside


def render(size, layers, bg):
    """layers: list of (colour, [shape tests]) painted in order over bg."""
    w, h = size
    rows = []
    for py in range(h):
        row = []
        for px in range(w):
            colour = list(bg)
            for fill, shapes in layers:
                hits = 0
                for sy in range(SS):
                    for sx in range(SS):
                        x, y = px + (sx + 0.5) / SS, py + (sy + 0.5) / SS
                        if any(s(x, y) for s in shapes):
                            hits += 1
                if hits:
                    a = hits / (SS * SS)
                    colour = [round(c * (1 - a) + f * a) for c, f in zip(colour, fill)]
            row.append(tuple(colour))
        rows.append(row)
    return rows


def strip(path, size, frames, bg):
    """Stack several frames vertically into one subimage strip."""
    rows = []
    for layers in frames:
        rows += render(size, layers, bg)
    write_bmp(path, size[0], size[1] * len(frames), rows)


def scale(points, k, dx=0, dy=0):
    return [(x * k + dx, y * k + dy) for x, y in points]


def main(rockbox):
    wps = os.path.join(rockbox, "wps", "iris-r3")

    # Play/pause button: 88x88, accent icon on an overlay circle
    disc = (OVERLAY, [circle(44, 44, 44)])
    play = (ACCENT, [polygon([(35, 27), (35, 61), (65, 44)])])
    pause = (ACCENT, [rect(30, 28, 39, 60), rect(49, 28, 58, 60)])
    strip(os.path.join(wps, "play.bmp"), (88, 88), [[disc, play], [disc, pause]], BG)

    # Previous / next: 56x56
    prev = (TEXT, [rect(14, 16, 19, 40), polygon([(42, 16), (42, 40), (21, 28)])])
    nxt = (TEXT, [rect(37, 16, 42, 40), polygon([(14, 16), (14, 40), (35, 28)])])
    strip(os.path.join(wps, "skip.bmp"), (56, 56), [[prev], [nxt]], BG)

    # Shuffle: 44x44, off / on (drawn on a 24-unit grid, scaled)
    k, sw = 44 / 24, 3.6
    shuffle_paths = [
        [(3, 7), (7, 7), (17, 17), (21, 17)],
        [(3, 17), (7, 17), (17, 7), (21, 7)],
        [(18, 4), (21, 7), (18, 10)],
        [(18, 14), (21, 17), (18, 20)],
    ]
    shuffle_shapes = [stroke(scale(p, k), sw) for p in shuffle_paths]
    strip(os.path.join(wps, "shuffle.bmp"), (44, 44),
          [[(DIM, shuffle_shapes)], [(ACCENT, shuffle_shapes)]], BG)

    # Repeat: 44x44, off / all / one
    repeat_paths = [
        [(4, 12), (4, 7), (20, 7)],
        [(17, 4), (20, 7), (17, 10)],
        [(20, 12), (20, 17), (4, 17)],
        [(7, 20), (4, 17), (7, 14)],
    ]
    repeat_shapes = [stroke(scale(p, k), sw) for p in repeat_paths]
    one = circle(12 * k, 12 * k, 3.2)
    strip(os.path.join(wps, "repeat.bmp"), (44, 44),
          [[(DIM, repeat_shapes)], [(ACCENT, repeat_shapes)], [(ACCENT, repeat_shapes + [one])]], BG)

    # Playback dot on the status strip: 12x12, playing / paused / stopped
    strip(os.path.join(wps, "dot.bmp"), (12, 12), [
        [(ACCENT, [circle(6, 6, 6)])],
        [(ACCENT, [rect(0, 0, 12, 12)])],
        [(ACCENT, [rect(0, 0, 12, 12)]), (OVERLAY, [rect(2, 2, 10, 10)])],
    ], OVERLAY)

    # Blank iconset: indents list rows. 32 themeable icons, 16x24 each
    write_bmp(os.path.join(rockbox, "icons", "iris-r3-blank.bmp"), 16, 24 * 32,
              [[MAGENTA] * 16 for _ in range(24 * 32)])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
