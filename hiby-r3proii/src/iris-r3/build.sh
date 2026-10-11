#!/usr/bin/env bash
#
# Regenerate iris-r3's fonts and bitmaps into hiby-r3proii/.rockbox.
#
#   hiby-r3proii/src/iris-r3/build.sh
#
# Uses convttf and Inter from tools/setup.sh. Skin files (.wps/.sbs/.cfg) are
# plain text and need no build step.

set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../../.." && pwd)"
work="${THEMES_WORK:-$repo/reference}"
out="$repo/hiby-r3proii/.rockbox"

convttf="$work/rockbox/tools/convttf"
inter="$work/inter/extras/ttf"
[[ -x "$convttf" && -d "$inter" ]] || { echo "Error: run tools/setup.sh first (needs convttf and Inter)." >&2; exit 1; }

"$here/make_fonts.sh" "$inter" "$convttf" "$out/fonts"
cp "$work/inter/LICENSE.txt" "$out/fonts/Inter-License.txt"
python3 -I "$here/make_bitmaps.py" "$out"
echo "Bitmaps written to $out"
