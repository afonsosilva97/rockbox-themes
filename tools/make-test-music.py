#!/usr/bin/env python3
"""Create a small silent test library on a (simulated) SD card.

Usage: python3 make-test-music.py <card-root>

Writes tagged WAV files (8 kHz, silent) under <card-root>/Music: one album
with cover art and a long title that has to scroll, and one track without
cover art. Rockbox reads WAV tags from the LIST/INFO chunk and picks up
cover.bmp as album art (as a BMP, only the name "cover" is recognised).
"""
import math
import os
import struct
import sys


def info_chunk(tags):
    body = b"INFO"
    for key, value in tags.items():
        data = value.encode() + b"\0"
        size = len(data)
        if size % 2:
            data += b"\0"
        body += key.encode() + struct.pack("<I", size) + data
    return b"LIST" + struct.pack("<I", len(body)) + body


def write_wav(path, seconds, title, artist, album, track):
    rate = 8000
    audio = b"\x80" * (rate * seconds)  # 8-bit unsigned silence
    fmt = struct.pack("<HHIIHH", 1, 1, rate, rate, 1, 8)
    tags = info_chunk({"INAM": title, "IART": artist, "IPRD": album, "IPRT": str(track)})
    chunks = (b"fmt " + struct.pack("<I", len(fmt)) + fmt + tags
              + b"data" + struct.pack("<I", len(audio)) + audio)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks)


def write_cover(path, size=500):
    """Soft rose and teal blobs on a dark grey, 24-bit BMP."""
    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            u, v = x / size, y / size
            rose = max(0.0, 1 - math.hypot(u - 0.4, v - 0.4) / 0.45)
            teal = max(0.0, 1 - math.hypot(u - 0.7, v - 0.72) / 0.5)
            r = 64 + 171 * rose
            g = 61 + 127 * rose + 55 * teal
            b = 82 + 104 * rose + 61 * teal
            row += bytes((min(255, int(b)), min(255, int(g)), min(255, int(r))))
        rows.append(bytes(row))
    data = b"".join(reversed(rows))
    header = struct.pack("<2sIHHI", b"BM", 54 + len(data), 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, size, size, 1, 24, 0, len(data), 2835, 2835, 0, 0)
    with open(path, "wb") as f:
        f.write(header + info + data)


def main(root):
    album = os.path.join(root, "Music", "Frank Ocean", "Blonde")
    write_wav(os.path.join(album, "01 Pink + White.wav"), 244, "Pink + White", "Frank Ocean", "Blonde", 1)
    write_wav(os.path.join(album, "02 Long title.wav"), 300,
              "A Really Long Track Title That Should Scroll Across The Whole Screen",
              "Frank Ocean", "Blonde", 2)
    write_wav(os.path.join(album, "03 Nights.wav"), 307, "Nights", "Frank Ocean", "Blonde", 3)
    write_cover(os.path.join(album, "cover.bmp"))

    no_art = os.path.join(root, "Music", "No Art", "Untitled")
    write_wav(os.path.join(no_art, "01 No Album Art.wav"), 180, "No Album Art Here", "Test Artist", "Untitled", 1)
    print(f"Test music written to {os.path.join(root, 'Music')}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
