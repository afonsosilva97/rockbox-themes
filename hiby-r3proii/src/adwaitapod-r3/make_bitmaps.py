#!/usr/bin/env python3
"""Generate the adwaitapod-r3 bitmaps for both variants (no dependencies).

Usage: python3 make_bitmaps.py <device-folder>/.rockbox <adwaita-symbolic-dir>

<adwaita-symbolic-dir> is Adwaita/symbolic from GNOME's adwaita-icon-theme
47.0 (tools/setup.sh downloads it). Icons are drawn with svgicon.py; shapes
are rasterised with 4x4 supersampling.

Formats: images that always sit on the same solid colour are pre-blended onto
it and saved as 8-bit palette BMPs, with magenta (FF00FF, Rockbox's
transparent colour) where nothing is drawn. Glyphs that sit on several
colours (status icons, list icons, the lock screen) are 32-bit BMPs with
alpha. The lock screen wallpaper is a dithered 24-bit BMP.
"""
import glob
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import svgicon  # noqa: E402
from variants import ACCENT, VARIANTS, WHITE  # noqa: E402

SS = 4
MAGENTA = (0xFF, 0x00, 0xFF)

# Rockbox's 32 themable list icons, in enum order (apps/gui/icon.h)
LIST_ICONS = [
    "audio-x-generic",          # audio file; also "Database" in the main menu
    "folder",                   # folder
    "view-list-bullet",         # playlist; also "Playlists"
    "go-next",                  # cursor
    "applications-graphics",    # theme file
    "application-x-firmware",   # firmware
    "font-x-generic",           # font
    "preferences-desktop-locale",  # language
    "preferences-system",       # config file
    "application-x-addon",      # plugin
    "starred",                  # bookmark; also "Shortcuts"
    "view-pin",                 # radio preset
    "media-playlist-consecutive",  # queued track
    "list-drag-handle",         # track being moved
    "input-keyboard",           # keyboard
    "go-previous",              # reverse cursor
    "dialog-question",          # unknown
    "document-properties",      # setting
    "help-about",               # function
    "radio-checked",            # submenu; also the "selected" mark in option lists
    "emblem-system",            # "Settings" in the main menu
    "audio-input-microphone",   # recording
    "chat-message-new",         # voice
    "preferences-system",       # general settings
    "multimedia-player",        # system
    "media-playback-start",     # "Now Playing" / playback settings
    "video-display",            # display settings
    "tv",                       # remote display settings
    "network-cellular",         # radio
    "system-file-manager",      # "Files"
    "multimedia-volume-control",  # equalizer
    "go-home",                  # Rockbox
]
# viewers.config icon numbers 0-12 (games, text, images, video, audio, ...)
VIEWER_ICONS = ["input-gaming", "text-x-generic", "image-x-generic", "text-x-generic",
                "video-x-generic", "audio-x-generic", "input-gaming", "audio-x-generic",
                "text-x-generic", "text-x-generic", "audio-x-generic", "image-x-generic",
                "input-gaming"]
LIST_CELL = (56, 31)  # list text starts after the cell; 31 px matches the list font


# ---------------------------------------------------------------- BMP output

def _header(path, width, height, bpp, data, palette=b"", colours=0):
    offset = 54 + len(palette)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(struct.pack("<2sIHHI", b"BM", offset + len(data), 0, 0, offset))
        f.write(struct.pack("<IiiHHIIiiII", 40, width, height, 1, bpp, 0, len(data),
                            2835, 2835, colours, 0) + palette)
        f.write(data)


def write_bmp24(path, rows):
    """rows of (r, g, b): 24-bit BMP."""
    stride = (len(rows[0]) * 3 + 3) & ~3
    data = bytearray()
    for row in reversed(rows):
        line = b"".join(bytes((b, g, r)) for r, g, b in row)
        data += line + b"\0" * (stride - len(line))
    _header(path, len(rows[0]), len(rows), 24, data)


def write_bmp(path, rows):
    """rows of (r, g, b): 8-bit palette BMP, or 24-bit past 256 colours."""
    h, w = len(rows), len(rows[0])
    palette = sorted({px for row in rows for px in row})
    if len(palette) > 256:
        write_bmp24(path, rows)
        return
    index = {c: i for i, c in enumerate(palette)}
    stride = (w + 3) & ~3
    data = bytearray()
    for row in reversed(rows):
        line = bytes(index[px] for px in row)
        data += line + b"\0" * (stride - len(line))
    table = b"".join(bytes((b, g, r, 0)) for r, g, b in palette)
    _header(path, w, h, 8, data, table, len(palette))


def write_bmp32(path, rows):
    """rows of (r, g, b, a): 32-bit BMP with alpha."""
    data = bytearray()
    for row in reversed(rows):
        for r, g, b, a in row:
            data += bytes((b, g, r, a))
    _header(path, len(rows[0]), len(rows), 32, data)


# ---------------------------------------------------------------- drawing

class Canvas:
    """RGBA canvas (straight alpha, floats) painted with coverage masks."""

    def __init__(self, w, h, fill=None):
        self.w, self.h = w, h
        c = (list(fill) + [1.0]) if fill else [0, 0, 0, 0.0]
        self.px = [[list(c) for _ in range(w)] for _ in range(h)]

    def paint(self, cov, colour, opacity=1.0):
        """Paint colour through a coverage mask the size of the canvas."""
        for y, row in enumerate(cov):
            dst = self.px[y]
            for x, c in enumerate(row):
                a = min(1.0, c) * opacity
                if a <= 0:
                    continue
                p = dst[x]
                out = a + p[3] * (1 - a)
                for i in range(3):
                    p[i] = (colour[i] * a + p[i] * p[3] * (1 - a)) / out
                p[3] = out
        return self

    def frame(self):
        """Rows for write_bmp: solid pixels as is, empty ones magenta."""
        return [[tuple(round(v) for v in p[:3]) if p[3] > 0.004 else MAGENTA for p in row]
                for row in self.px]

    def rgba(self):
        return [[(round(p[0]), round(p[1]), round(p[2]), round(p[3] * 255)) for p in row]
                for row in self.px]


def cov(w, h, inside):
    """Coverage of a shape test inside(x, y) on a w x h grid."""
    rows = []
    for py in range(h):
        row = []
        for px in range(w):
            hits = sum(inside(px + (sx + 0.5) / SS, py + (sy + 0.5) / SS)
                       for sy in range(SS) for sx in range(SS))
            row.append(hits / (SS * SS))
        rows.append(row)
    return rows


def rrect(x0, y0, x1, y1, r):
    def inside(x, y):
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            return False
        cx = min(max(x, x0 + r), x1 - r)
        cy = min(max(y, y0 + r), y1 - r)
        return (x - cx) ** 2 + (y - cy) ** 2 <= r * r
    return inside


def circle(cx, cy, r):
    return lambda x, y: (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def shadow(w, h, x0, y0, x1, y1, r, blur):
    """Soft shadow alpha of a rounded rect: falls off over blur px outside it."""
    rows = []
    for py in range(h):
        row = []
        for px in range(w):
            x, y = px + 0.5, py + 0.5
            cx = min(max(x, x0 + r), x1 - r)
            cy = min(max(y, y0 + r), y1 - r)
            d = math.hypot(x - cx, y - cy) - r
            t = min(1.0, max(0.0, d / blur))
            row.append((1 - t) ** 2 if d > 0 else 1.0)
        rows.append(row)
    return rows


class Icons:
    def __init__(self, root):
        self.root = root

    def __call__(self, name, px, size=None, offset=(0, 0)):
        path = glob.glob(os.path.join(self.root, "*", f"{name}-symbolic.svg"))
        if not path:
            sys.exit(f"Adwaita icon not found: {name}")
        return svgicon.render(path[0], px, size, offset)


def centred(icon, name, px, size):
    return icon(name, px, size, ((size[0] - px) / 2, (size[1] - px) / 2))


def stack(frames):
    return [row for f in frames for row in f]


# ---------------------------------------------------------------- images

def make_variant(rockbox, theme, v, icon):
    out = os.path.join(rockbox, "wps", theme)
    save = lambda name, rows: write_bmp(os.path.join(out, name), rows)
    save32 = lambda name, rows: write_bmp32(os.path.join(out, name), rows)
    glyph = lambda name, px, colour, size=None: Canvas(*(size or (px, px))).paint(
        centred(icon, name, px, size or (px, px)), colour).rgba()

    # status bar: back, lock, battery levels (0-100 in steps of 10) and charging
    save32("back.bmp", glyph("go-previous", 24, v["fg"]))
    save32("lock.bmp", glyph("system-lock-screen", 24, v["fg"]))
    save32("lockw.bmp", glyph("system-lock-screen", 24, v["lock_fg"]))
    levels = {"batt": [f"battery-level-{n}" for n in range(0, 101, 10)],
              "battc": [f"battery-level-{n}-charging" for n in range(0, 100, 10)] + ["battery-level-100-charged"]}
    for name, icons in levels.items():
        for colour, suffix in ((v["fg"], ""), (v["lock_fg"], "w")):
            save32(f"{name}{suffix}.bmp", stack(glyph(n, 24, colour) for n in icons))

    # ---- home screen widgets (base skin), on the background colour
    # analog clock: face + minute hand (60 frames), hour hand overlay (12)
    R = 36
    frames = []
    for m in list(range(1, 60)) + [0]:
        c = Canvas(72, 72).paint(cov(72, 72, circle(R, R, R)), v["card"])
        for k in range(12):
            a = math.radians(k * 30)
            c.paint(cov(72, 72, circle(R + 29 * math.sin(a), R - 29 * math.cos(a), 1.6 if k % 3 else 2.4)), v["dim"])
        a = math.radians(m * 6)
        c.paint(cov(72, 72, hand(R, a, 27, 3)), v["fg"])
        frames.append(blend_on(c, v["bg"]))
    save("clockm.bmp", stack(frames))
    frames = []
    for hr in range(1, 13):
        c = Canvas(72, 72).paint(cov(72, 72, hand(R, math.radians(hr * 30), 17, 4.5)), v["fg"])
        c.paint(cov(72, 72, circle(R, R, 4)), ACCENT)
        frames.append(blend_on(c, v["card"]))
    save("clockh.bmp", stack(frames))

    # volume pill: static backdrop and left cap; the bar is a fill + a "D" knob
    W, H = 392, 48
    save("volbg.bmp", blend_on(Canvas(W, H).paint(cov(W, H, rrect(0, 0, W, H, 24)), v["track"]), v["bg"]))
    save("volcap.bmp", blend_on(Canvas(24, H).paint(cov(24, H, rrect(0, 0, 48, H, 24)), ACCENT), v["bg"]))
    save("volbk.bmp", blend_on(Canvas(W - 24, H).paint(cov(W - 24, H, rrect(-30, 0, W - 24, H, 24)), v["track"]), v["bg"]))
    save("volfill.bmp", Canvas(W - 24, H, ACCENT).frame())
    save("volknob.bmp", blend_on(Canvas(48, H).paint(cov(48, H, rrect(-24, 0, 48, H, 24)), ACCENT), v["track"]))
    save32("volf.bmp", stack(glyph(f"audio-volume-{n}", 24, v["fg"]) for n in ("muted", "low", "medium", "high")))

    # shuffle / repeat pills: off, on
    save("pill.bmp", stack(blend_on(Canvas(210, 48).paint(cov(210, 48, rrect(0, 0, 210, 48, 24)), c), v["bg"])
                           for c in (v["track"], ACCENT)))
    save32("shufp.bmp", stack([glyph("media-playlist-shuffle", 24, v["fg"]),
                               glyph("media-playlist-shuffle", 24, WHITE)]))
    save32("repp.bmp", stack([glyph("media-playlist-repeat", 24, v["fg"]),
                              glyph("media-playlist-repeat", 24, WHITE),
                              glyph("media-playlist-repeat-song", 24, WHITE)]))

    # ---- mini player (menus while playing), on the header colour; on the home
    # screen it sits on a header-coloured card
    save("hcard.bmp", blend_on(Canvas(432, 80).paint(cov(432, 80, rrect(0, 0, 432, 80, 16)), v["header"]), v["bg"]))
    save("mcorner.bmp", corners(8, v["header"]))
    na = Canvas(56, 56).paint(cov(56, 56, rrect(0, 0, 56, 56, 8)), v["track"])
    na.paint(centred(icon, "audio-x-generic", 28, (56, 56)), v["dim"])
    save("mnoart.bmp", blend_on(na, v["header"]))
    save("mplay.bmp", stack(blend_on(Canvas(48, 48).paint(cov(48, 48, circle(24, 24, 24)), ACCENT)
                                     .paint(centred(icon, n, 22, (48, 48)), WHITE), v["header"])
                            for n in ("media-playback-start", "media-playback-pause")))

    # ---- quick screen, on the background colour
    save("qsbatt.bmp", blend_on(Canvas(160, 56).paint(cov(160, 56, rrect(0, 0, 160, 56, 28)), v["card"]), v["bg"]))
    save("qsback.bmp", blend_on(Canvas(56, 56).paint(cov(56, 56, circle(28, 28, 28)), v["card"])
                                .paint(centred(icon, "edit-undo", 24, (56, 56)), v["fg"]), v["bg"]))
    save32("bright.bmp", glyph("display-brightness", 24, v["fg"]))

    # ---- thin sliders with a knob: seek bar and quick screen (400 px, on the
    # background), volume pop-up (296 px, on a card)
    for name, w, under in (("seek", 400, v["bg"]), ("osd", 296, v["card"])):
        save(f"{name}bk.bmp", blend_on(Canvas(w, 24).paint(cov(w, 24, rrect(0, 9, w, 15, 3)), v["track"]), under))
        save(f"{name}fill.bmp", blend_on(Canvas(w, 24).paint(cov(w, 24, rrect(0, 9, w + 6, 15, 3)), ACCENT), under))
        k = Canvas(24, 24).paint(shadow(24, 24, 2, 3, 22, 23, 10, 3), (0, 0, 0), v["shadow"])
        k.paint(cov(24, 24, circle(12, 12, 10)), WHITE)
        save(f"{name}knob.bmp", blend_on(k, under))

    # ---- now playing
    A, P = 360, 16  # art size, shadow padding
    s = Canvas(A + 2 * P, A + 2 * P, v["bg"])
    s.paint(shadow(A + 2 * P, A + 2 * P, P, P + 4, P + A, P + A + 4, 16, 14), (0, 0, 0), v["shadow"])
    save("artshadow.bmp", s.frame())
    save("corner.bmp", corners(16, v["bg"]))
    na = Canvas(A, A).paint(cov(A, A, rrect(0, 0, A, A, 16)), v["card"])
    na.paint(centred(icon, "audio-x-generic", 128, (A, A)), v["track"])
    save("noart.bmp", blend_on(na, v["bg"]))
    save32("skip.bmp", stack([glyph("media-skip-backward", 32, v["fg"]), glyph("media-skip-forward", 32, v["fg"])]))
    save("play.bmp", stack(blend_on(Canvas(120, 64).paint(cov(120, 64, rrect(0, 0, 120, 64, 32)), ACCENT)
                                    .paint(centred(icon, n, 30, (120, 64)), WHITE), v["bg"])
                           for n in ("media-playback-start", "media-playback-pause")))
    save32("shuf.bmp", stack([glyph("media-playlist-shuffle", 28, v["dim"]),
                              glyph("media-playlist-shuffle", 28, ACCENT)]))
    save32("rep.bmp", stack([glyph("media-playlist-repeat", 28, v["dim"]),
                             glyph("media-playlist-repeat", 28, ACCENT),
                             glyph("media-playlist-repeat-song", 28, ACCENT)]))
    save("osd.bmp", blend_on(Canvas(400, 64).paint(cov(400, 64, rrect(0, 0, 400, 64, 32)), v["card"]), v["bg"]))

    # ---- lock screen
    write_bmp24(os.path.join(out, "wall.bmp"), wallpaper(v["wall_base"], v["wall_blobs"]))
    colour, alpha = v["lock_card"]
    save32("lcard.bmp", Canvas(432, 112).paint(cov(432, 112, rrect(0, 0, 432, 112, 24)), colour, alpha).rgba())
    n = Canvas(80, 80).paint(cov(80, 80, rrect(0, 0, 80, 80, 12)), colour, alpha)
    n.paint(centred(icon, "audio-x-generic", 36, (80, 80)), v["lock_fg"])
    save32("lnote.bmp", n.rgba())
    save32("lplay.bmp", stack([glyph("media-playback-start", 28, v["lock_fg"]),
                               glyph("media-playback-pause", 28, v["lock_fg"])]))

    # ---- list icons (32-bit: they sit on the background and the selection bar)
    cw, ch = LIST_CELL
    cell = lambda name: Canvas(cw, ch).paint(icon(name, 24, (cw, ch), (16, (ch - 24) / 2)), v["fg"]).rgba()
    write_bmp32(os.path.join(rockbox, "icons", f"{theme}-icons.bmp"), stack(cell(n) for n in LIST_ICONS))
    write_bmp32(os.path.join(rockbox, "icons", f"{theme}-viewers.bmp"), stack(cell(n) for n in VIEWER_ICONS))


def hand(c, angle, length, width):
    """A clock hand from the centre, round-capped."""
    ex, ey = c + length * math.sin(angle), c - length * math.cos(angle)
    half = width / 2

    def inside(x, y):
        dx, dy = ex - c, ey - c
        t = max(0.0, min(1.0, ((x - c) * dx + (y - c) * dy) / (dx * dx + dy * dy)))
        return math.hypot(x - (c + t * dx), y - (c + t * dy)) <= half
    return inside


def corners(r, colour):
    """Album art corner masks (top-left, top-right, bottom-left, bottom-right):
    the area outside a radius-r rounded corner, in the colour around the art."""
    frames = []
    for fx, fy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        cx, cy = (r if not fx else 0), (r if not fy else 0)
        outside = lambda x, y, cx=cx, cy=cy, fx=fx, fy=fy: (
            ((x < cx) if not fx else (x > cx)) and ((y < cy) if not fy else (y > cy))
            and (x - cx) ** 2 + (y - cy) ** 2 > r * r)
        frames.append(Canvas(r, r).paint(cov(r, r, outside), colour).frame())
    return stack(frames)


def blend_on(canvas, bg):
    """Pre-blend onto a solid colour; pixels with nothing drawn become magenta."""
    return [[MAGENTA if a <= 0.004 else tuple(round(c * a + k * (1 - a)) for c, k in zip((r, g, b), bg))
             for r, g, b, a in row] for row in canvas.px]


def wallpaper(base, blobs):
    """Soft colour blobs over a base colour, ordered-dithered for the 16-bit LCD.
    blobs: (colour, centre x, centre y, radius), as fractions of the width."""
    W, H = 480, 720
    bayer = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
    rows = []
    for y in range(H):
        row = []
        for x in range(W):
            c = list(base)
            for colour, bx, by, rad in blobs:
                d = math.hypot(x / W - bx, (y / H - by) * H / W) / rad
                a = max(0.0, 1 - d * d) ** 2 * 0.9
                c = [k * (1 - a) + n * a for k, n in zip(c, colour)]
            t = (bayer[y % 4][x % 4] + 0.5) / 16 - 0.5
            row.append((q(c[0] + t * 8, 3), q(c[1] + t * 4, 2), q(c[2] + t * 8, 3)))
        rows.append(row)
    return rows


def q(v, bits):
    """Cut to the LCD's precision (drop `bits` low bits), back to 8 bits."""
    v = max(0, min(255, round(v)))
    v = (v >> bits) << bits
    return v | (v >> (8 - bits))


def main(rockbox, symbolic):
    icon = Icons(symbolic)
    for theme, v in VARIANTS.items():
        make_variant(rockbox, theme, v, icon)
        print(theme)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
