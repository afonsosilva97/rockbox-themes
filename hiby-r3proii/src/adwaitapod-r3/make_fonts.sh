#!/usr/bin/env bash
#
# Build the adwaitapod-r3 bitmap fonts from Cantarell.
#
#   ./make_fonts.sh <cantarell-dir> <convttf> <output-dir>
#
# <cantarell-dir>  Cantarell-{Light,Regular,Bold}.otf: static instances of
#                  Cantarell 0.303.1's variable font (tools/setup.sh makes them
#                  with fontTools' varLib.instancer at weights 300, 400, 700)
# <convttf>        Rockbox's tools/convttf, built with FreeType:
#                  cc -O2 -o convttf tools/convttf.c $(pkg-config --cflags --libs freetype2)
#
# convttf writes 4-bit anti-aliased .fnt files. The number in each name is the
# convttf pixel size; the resulting line heights are 23, 27, 29, 31, 37 and 151 px.

set -euo pipefail

[[ $# -eq 3 ]] || { echo "Usage: $0 <cantarell-dir> <convttf> <output-dir>" >&2; exit 1; }
otf="$1"; convttf="$2"; out="$3"
mkdir -p "$out"

# weight  size  first-char  last-char
fonts=(
  "Regular 22  32 8364"   # times, artist in the mini player, album, hints
  "Bold    26  32 8364"   # status bar title, buttons, mini player title
  "Bold    28  32 8364"   # home greeting, lock screen track title
  "Regular 30  32 8364"   # lists (theme font), artist on Now Playing, dates
  "Bold    36  32 8364"   # track title on Now Playing
  "Light   150 32 58"     # lock screen clock: digits and colon only
)

for spec in "${fonts[@]}"; do
  read -r weight size first last <<< "$spec"
  "$convttf" -p "$size" -s "$first" -l "$last" \
    -o "$out/$size-Cantarell-$weight.fnt" "$otf/Cantarell-$weight.otf" > /dev/null
  echo "$out/$size-Cantarell-$weight.fnt"
done
