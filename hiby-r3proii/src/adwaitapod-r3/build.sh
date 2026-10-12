#!/usr/bin/env bash
#
# Regenerate adwaitapod-r3 (light and dark) into hiby-r3proii/.rockbox:
# fonts, bitmaps, skins and theme files.
#
#   hiby-r3proii/src/adwaitapod-r3/build.sh
#
# Uses convttf, Cantarell and the Adwaita icons from tools/setup.sh.

set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../../.." && pwd)"
work="${THEMES_WORK:-$repo/reference}"
out="$repo/hiby-r3proii/.rockbox"

convttf="$work/rockbox/tools/convttf"
cantarell="$work/cantarell"
symbolic="$work/adwaita-icons/Adwaita/symbolic"
[[ -x "$convttf" && -f "$cantarell/Cantarell-Bold.otf" && -d "$symbolic" ]] ||
  { echo "Error: run tools/setup.sh first (needs convttf, Cantarell and the Adwaita icons)." >&2; exit 1; }

"$here/make_fonts.sh" "$cantarell" "$convttf" "$out/fonts"
cp "$cantarell/COPYING" "$out/fonts/Cantarell-License.txt"
python3 -I "$here/make_skins.py" "$out"
python3 -I "$here/make_bitmaps.py" "$out" "$symbolic"
echo "adwaitapod-r3 written to $out"
