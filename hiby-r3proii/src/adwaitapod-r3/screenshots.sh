#!/usr/bin/env bash
#
# Regenerate adwaitapod-r3's screenshots (light and dark) with the simulator
# and re-embed them in the preview page.
#
#   hiby-r3proii/src/adwaitapod-r3/screenshots.sh
#
# Drives the simulator through scripted taps (the RB_TEST_SCRIPT hook from
# tools/setup.sh) and writes hiby-r3proii/screenshots/<theme>*.png for
# <theme> = adwaitapod-r3 and adwaitapod-r3-dark:
#   <theme>-home.png          main menu, nothing playing
#   <theme>.png               Now Playing with album art
#   <theme>-quick.png         quick screen (flick down from the top edge)
#   <theme>-lock.png          lock screen
#   <theme>-home-playing.png  main menu while playing
#   <theme>-menu.png          Settings, with the mini player
#   <theme>-no-art.png        Now Playing for a track without art
# The taps assume adwaitapod-r3's layout (56 px list rows from y=56) and the
# test music from tools/make-test-music.py. If reference/test-cover.{jpg,jpeg,png}
# exists it's used as the album cover (it stays out of git; only the
# screenshots show it). The simulator window opens briefly.

set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../../.." && pwd)"
device="$repo/hiby-r3proii"
work="${THEMES_WORK:-$repo/reference}"
sim="$work/rockbox/build-sim"
disk="$sim/simdisk"
out="$device/screenshots"
[[ -x "$sim/rockboxui" ]] || { echo "Error: run tools/setup.sh first." >&2; exit 1; }

"$repo/install.sh" "$device" "$disk" > /dev/null
cover=()
for f in "$work"/test-cover.{jpg,jpeg,png}; do [[ -f "$f" ]] && cover=("$f") && break; done
python3 -I "$repo/tools/make-test-music.py" "$disk" ${cover[@]+"${cover[@]}"} > /dev/null

# run <theme> <script> <name>...: replay taps, then save each screendump in order
run() {
  local theme="$1" script="$2"; shift 2
  cp "$device/.rockbox/themes/$theme.cfg" "$disk/.rockbox/config.cfg"
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
# Music folders sort as: No Art (row y=84), Sade (140), Test (196)
open_track() { echo "5000 down 100 84;5100 up;6500 down 100 84;6600 up;8000 down 100 $1;8100 up;9500 down 100 84;9600 up;11000 down 100 84;11100 up"; }

for theme in adwaitapod-r3 adwaitapod-r3-dark; do
  # home; Now Playing; quick screen (a fast drag down from the top edge) and
  # back; key lock (power, then + vol up) and unlock; back to the menu; Settings
  run "$theme" "3000 dump;$(open_track 140);14000 dump;14500 down 240 4;14530 down 240 80;14560 down 240 180;14590 down 240 300;14620 up;16000 dump;16500 down 430 52;16600 up;18000 keys 1;18300 keys 11;18600 keys 0;20500 dump;21000 keys 1;21300 keys 11;21600 keys 0;23000 down 40 30;23100 up;24500 dump;25000 down 100 252;25100 up;26500 dump;27000 quit" \
    "$theme-home" "$theme" "$theme-quick" "$theme-lock" "$theme-home-playing" "$theme-menu"
  run "$theme" "$(open_track 84);14000 dump;15000 quit" "$theme-no-art"
done
echo "Screenshots written to $out"

# Re-embed in the preview page, in the order its figures appear
python3 -I - "$device/previews/adwaitapod-r3.html" "$out" <<'EOF'
import base64, re, sys
page, shots = sys.argv[1], sys.argv[2]
html = open(page).read()
order = [f"{theme}{suffix}" for theme in ("adwaitapod-r3", "adwaitapod-r3-dark")
         for suffix in ("-home", "", "-home-playing", "-menu", "-quick", "-lock", "-no-art")]
found = re.findall(r'src="data:image/png;base64,[^"]*"', html)
if len(found) != len(order):
    sys.exit(f"Expected {len(order)} embedded images in {page}, found {len(found)}")
for old, name in zip(found, order):
    data = base64.b64encode(open(f"{shots}/{name}.png", "rb").read()).decode()
    html = html.replace(old, f'src="data:image/png;base64,{data}"', 1)
open(page, "w").write(html)
print(f"Updated {page}")
EOF
