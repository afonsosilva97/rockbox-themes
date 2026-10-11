#!/usr/bin/env python3
"""Create a small silent test library on a (simulated) SD card.

Usage: python3 make-test-music.py <card-root> [cover-image]

Writes tagged WAV files (8 kHz, silent) under <card-root>/Music:
  Sade/Love Deluxe     album with cover art ("Like a Tattoo" is the main track)
  No Art/Untitled      a track without cover art
  Test/Long Titles     a title long enough to have to scroll
Rockbox reads WAV tags from the LIST/INFO chunk and picks up cover.bmp as
album art (as a BMP, only the name "cover" is recognised). If [cover-image]
is given (any format macOS `sips` reads), it's converted to that cover;
otherwise an abstract cover is generated.
"""
import math
import os
import shutil
import struct
import subprocess
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


def main(root, cover_image=None):
    music = os.path.join(root, "Music")
    shutil.rmtree(music, ignore_errors=True)

    album = os.path.join(music, "Sade", "Love Deluxe")
    for number, title, seconds in [(4, "Like a Tattoo", 218), (5, "Kiss of Life", 330), (6, "Cherish the Day", 336)]:
        write_wav(os.path.join(album, f"{number:02d} {title}.wav"), seconds, title, "Sade", "Love Deluxe", number)
    cover = os.path.join(album, "cover.bmp")
    if cover_image:
        # 24-bit BMP, at most 500 px (never upscaled): Rockbox scales it to the skin's art size
        size = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", cover_image],
                              check=True, capture_output=True, text=True).stdout.split()
        resize = ["-Z", "500"] if max(int(size[-3]), int(size[-1])) > 500 else []
        subprocess.run(["sips", "-s", "format", "bmp", *resize, cover_image, "--out", cover],
                       check=True, stdout=subprocess.DEVNULL)
    else:
        write_cover(cover)

    write_wav(os.path.join(music, "No Art", "Untitled", "01 No Album Art.wav"), 180,
              "No Album Art Here", "Test Artist", "Untitled", 1)
    write_wav(os.path.join(music, "Test", "Long Titles", "01 Long title.wav"), 300,
              "A Really Long Track Title That Should Scroll Across The Whole Screen",
              "Test Artist", "Long Titles", 1)
    print(f"Test music written to {music}")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    main(*sys.argv[1:])
