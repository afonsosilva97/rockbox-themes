#!/usr/bin/env bash
#
# Validate every theme of a device with checkwps.
#
#   tools/check.sh <device-folder>
#
# Checks each themes/*.cfg and the .wps/.sbs files it points to against the
# device's screen size, fonts and images. Needs tools/setup.sh to have run.

set -euo pipefail

[[ $# -eq 1 ]] || { echo "Usage: $0 <device-folder>" >&2; exit 1; }

repo="$(cd "$(dirname "$0")/.." && pwd)"
device="$(cd "$1" && pwd)"
work="${THEMES_WORK:-$repo/reference}"
checkwps="$(ls "$work"/rockbox/build-checkwps/checkwps.* 2> /dev/null | head -1)"
[[ -x "$checkwps" ]] || { echo "Error: checkwps not found. Run tools/setup.sh first." >&2; exit 1; }

# checkwps resolves fonts and images relative to the folder holding .rockbox/
cd "$device"
failed=0
for cfg in .rockbox/themes/*.cfg; do
  files=("$cfg")
  for key in wps sbs fms; do
    path="$(sed -n "s|^$key: */||p" "$cfg" | tr -d '\r')"
    [[ -n "$path" && "$path" != "-" ]] && files+=("$path")
  done
  for f in "${files[@]}"; do
    if out="$("$checkwps" "$f" 2>&1)" && grep -q "parsed OK" <<< "$out"; then
      echo "ok    $f"
    else
      echo "FAIL  $f"; echo "$out" | sed 's/^/      /'
      failed=1
    fi
  done
done
exit $failed
