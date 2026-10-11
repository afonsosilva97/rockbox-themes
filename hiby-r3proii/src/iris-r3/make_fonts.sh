#!/usr/bin/env bash
#
# Build the iris-r3 bitmap fonts from Inter's static TTFs.
#
#   ./make_fonts.sh <inter-ttf-dir> <convttf> <output-dir>
#
# <inter-ttf-dir>  extras/ttf from the Inter 4.1 release zip
#                  (https://github.com/rsms/inter/releases/tag/v4.1)
# <convttf>        Rockbox's tools/convttf, built with FreeType:
#                  cc -O2 -o convttf tools/convttf.c $(pkg-config --cflags --libs freetype2)
#
# convttf writes 4-bit anti-aliased .fnt files. The number in each name is the
# convttf pixel size; the resulting line heights are 22, 25, 32, 42 and 143 px.

set -euo pipefail

[[ $# -eq 3 ]] || { echo "Usage: $0 <inter-ttf-dir> <convttf> <output-dir>" >&2; exit 1; }
ttf="$1"; convttf="$2"; out="$3"
mkdir -p "$out"

# weight  size  first-char  last-char
fonts=(
  "SemiBold 20  32 8364"   # title bar, status clock
  "Regular  24  32 8364"   # album, times, playlist position
  "Medium   30  32 8364"   # lists (theme font), artist
  "Bold     40  32 8364"   # track title on Now Playing
  "SemiBold 140 32 58"     # lock screen clock: digits and colon only
)

for spec in "${fonts[@]}"; do
  read -r weight size first last <<< "$spec"
  "$convttf" -p "$size" -s "$first" -l "$last" \
    -o "$out/$size-Inter-$weight.fnt" "$ttf/Inter-$weight.ttf" > /dev/null
  echo "$out/$size-Inter-$weight.fnt"
done
