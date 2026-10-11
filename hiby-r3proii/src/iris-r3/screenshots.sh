#!/usr/bin/env bash
#
# Regenerate iris-r3's screenshots with the simulator and re-embed them in
# the preview page.
#
#   hiby-r3proii/src/iris-r3/screenshots.sh
#
# Drives the simulator through scripted taps (the RB_TEST_SCRIPT hook from
# tools/setup.sh) and writes hiby-r3proii/screenshots/iris-r3*.png:
#   iris-r3.png         Now Playing with album art
#   iris-r3-no-art.png  Now Playing for a track without art
#   iris-r3-menu.png    main menu while playing
#   iris-r3-lock.png    lock screen
# The taps assume iris-r3's layout (60 px list rows from y=80) and the test
# music from tools/make-test-music.py. The simulator window opens briefly.

set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../../.." && pwd)"
device="$repo/hiby-r3proii"
work="${THEMES_WORK:-$repo/reference}"
sim="$work/rockbox/build-sim"
disk="$sim/simdisk"
out="$device/screenshots"
[[ -x "$sim/rockboxui" ]] || { echo "Error: run tools/setup.sh first." >&2; exit 1; }

# Fresh copy of the theme and test music, so the taps land where expected
"$repo/install.sh" "$device" "$disk" > /dev/null
cp "$device/.rockbox/themes/iris-r3.cfg" "$disk/.rockbox/config.cfg"
rm -rf "$disk/Music"
python3 -I "$repo/tools/make-test-music.py" "$disk" > /dev/null

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# run <script> <name>...: replay taps, then save each screendump in order
run() {
  local script="$1"; shift
  rm -f "$disk"/dump*.bmp
  (cd "$sim" && RB_TEST_SCRIPT="$script" ./rockboxui --nobackground > /dev/null 2>&1)
  local dumps=()
  while IFS= read -r f; do dumps+=("$f"); done < <(ls "$disk" | grep '^dump .*\.bmp$' | sort)
  [[ ${#dumps[@]} -eq $# ]] || { echo "Error: expected $# screenshots, got ${#dumps[@]}" >&2; exit 1; }
  local i=0
  for name in "$@"; do
    sips -s format png "$disk/${dumps[$i]}" --out "$out/$name.png" > /dev/null
    rm "$disk/${dumps[$i]}"
    i=$((i + 1))
  done
}

# Main menu → Files → Music → <artist row y> → album → first track
open_track() { echo "5000 down 100 110;5100 up;6500 down 100 110;6600 up;8000 down 100 $1;8100 up;9500 down 100 110;9600 up;11000 down 100 110;11100 up"; }

# Now Playing; tap the header for the menu; back via "Now Playing"; hold the header to lock
run "$(open_track 110);14000 dump;14500 down 240 20;14600 up;16000 dump;16500 down 100 230;16600 up;18000 down 240 40;20000 up;21500 dump;22500 quit" \
  iris-r3 iris-r3-menu iris-r3-lock
# Track without album art (second artist folder)
run "$(open_track 170);14000 dump;15000 quit" iris-r3-no-art
echo "Screenshots written to $out"

# Re-embed in the preview page, in the order its figures appear
python3 -I - "$device/previews/iris-r3.html" "$out" <<'EOF'
import base64, re, sys
page, shots = sys.argv[1], sys.argv[2]
html = open(page).read()
order = ["iris-r3", "iris-r3-no-art", "iris-r3-menu", "iris-r3-lock"]
found = re.findall(r'src="data:image/png;base64,[^"]*"', html)
if len(found) != len(order):
    sys.exit(f"Expected {len(order)} embedded images in {page}, found {len(found)}")
for old, name in zip(found, order):
    data = base64.b64encode(open(f"{shots}/{name}.png", "rb").read()).decode()
    html = html.replace(old, f'src="data:image/png;base64,{data}"', 1)
open(page, "w").write(html)
print(f"Updated {page}")
EOF
