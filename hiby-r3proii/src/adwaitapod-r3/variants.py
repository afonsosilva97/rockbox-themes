"""adwaitapod-r3's two colour variants, shared by make_bitmaps.py and make_skins.py.

Colours follow Adwaitapod 3.4's light and dark themes, with GNOME's blue accent.
They are snapped to the LCD's 16-bit colours: Rockbox rounds skin colours
(%dr, %Vf) and bitmaps differently, so a colour between two 16-bit values
would show as two slightly different shades where an image meets a fill.
"""


def rgb565(c):
    """Nearest colour the 16-bit LCD shows exactly, back in 8 bits per channel.
    Greys stay neutral: green (6 bits) is matched to red and blue (5 bits)."""
    r, b = round(c[0] * 31 / 255), round(c[2] * 31 / 255)
    r, b = (r << 3) | (r >> 2), (b << 3) | (b >> 2)
    g = round((r if c[0] == c[1] == c[2] else c[1]) * 63 / 255)
    return (r, (g << 2) | (g >> 4), b)


ACCENT = rgb565((0x35, 0x84, 0xE4))
WHITE = (0xFF, 0xFF, 0xFF)

VARIANTS = {
    "adwaitapod-r3": dict(
        bg=(0xFA, 0xFA, 0xFA), header=(0xEB, 0xEB, 0xEB), border=(0xD6, 0xD6, 0xD6),
        card=(0xFF, 0xFF, 0xFF), select=(0xE3, 0xE3, 0xE3), track=(0xDE, 0xDD, 0xDA),
        fg=(0x29, 0x28, 0x29), dim=(0x6B, 0x6D, 0x6B), shadow=0.10,
        # lock screen: soft pale wallpaper, dark text, frosted white card
        wall_base=(0xE9, 0xE7, 0xF0),
        wall_blobs=[((0x99, 0xC1, 0xF1), 0.25, 0.20, 0.55), ((0xDC, 0xA6, 0xE6), 0.85, 0.35, 0.50),
                    ((0xB5, 0xD3, 0xF5), 0.30, 0.85, 0.60), ((0xF2, 0xC4, 0xD8), 0.90, 0.95, 0.45)],
        lock_fg=(0x29, 0x28, 0x29), lock_card=(WHITE, 0.5)),
    "adwaitapod-r3-dark": dict(
        bg=(0x29, 0x28, 0x29), header=(0x31, 0x30, 0x31), border=(0x21, 0x20, 0x21),
        card=(0x39, 0x38, 0x39), select=(0x52, 0x51, 0x52), track=(0x42, 0x41, 0x42),
        fg=WHITE, dim=(0xBD, 0xBA, 0xBD), shadow=0.35,
        # lock screen: deep blue and purple wallpaper, white text, frosted card
        wall_base=(0x1A, 0x16, 0x38),
        wall_blobs=[((0x35, 0x84, 0xE4), 0.80, 0.25, 0.55), ((0x91, 0x41, 0xAC), 0.15, 0.30, 0.55),
                    ((0x1C, 0x71, 0xD8), 0.25, 0.90, 0.55), ((0xC0, 0x61, 0xCB), 0.90, 0.85, 0.45)],
        lock_fg=WHITE, lock_card=(WHITE, 0.14)),
}
UI_COLOURS = ("bg", "header", "border", "card", "select", "track", "fg", "dim", "lock_fg")
for _v in VARIANTS.values():
    _v.update({k: rgb565(_v[k]) for k in UI_COLOURS})
