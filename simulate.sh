#!/usr/bin/env bash
#
# Try a device's themes in the Rockbox UI simulator instead of on the card.
#
#   ./simulate.sh <device-folder> [theme]
#
# Merges <device-folder>/.rockbox into the simulator's virtual SD card (with
# install.sh), optionally selects [theme], and opens the simulator window.
# The mouse acts as your finger. F5 saves a screenshot into the sim disk.
#
# Needs the simulator built by tools/setup.sh (see DEV.md). It lives in the
# gitignored reference/ folder, or $THEMES_WORK if set.

set -euo pipefail

usage() {
  echo "Usage: $0 <device-folder> [theme]" >&2
  echo "  e.g. $0 hiby-r3proii iris-r3" >&2
  exit 1
}

[[ $# -ge 1 && $# -le 2 ]] || usage

repo="$(cd "$(dirname "$0")" && pwd)"
device="${1%/}"
theme="${2:-}"
work="${THEMES_WORK:-$repo/reference}"
sim="$work/rockbox/build-sim"
disk="$sim/simdisk"

if [[ ! -x "$sim/rockboxui" || ! -d "$disk/.rockbox" ]]; then
  echo "Error: no simulator found in $sim." >&2
  echo "Build it first with tools/setup.sh (see DEV.md)." >&2
  exit 1
fi

"$repo/install.sh" "$repo/$device" "$disk" > /dev/null
echo "Installed $device themes into the simulator."

if [[ -n "$theme" ]]; then
  cfg="$repo/$device/.rockbox/themes/$theme.cfg"
  [[ -f "$cfg" ]] || { echo "Error: theme '$theme' not found at $cfg" >&2; exit 1; }
  # The simulator's own settings file; applying the theme's settings selects it.
  cp "$cfg" "$disk/.rockbox/config.cfg"
  echo "Selected $theme."
fi

echo "Opening the simulator. Close its window to quit."
cd "$sim" && exec ./rockboxui
