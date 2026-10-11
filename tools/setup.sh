#!/usr/bin/env bash
#
# Build the local tools for working on themes (macOS):
#   - checkwps   validates skins against the device's screen
#   - convttf    converts TTF fonts to anti-aliased Rockbox .fnt files
#   - simulator  the Rockbox UI for the device, with silent test music
#   - Inter      the font used by iris-r3, for rebuilding its .fnt files
#
#   tools/setup.sh [--target <rockbox-target>] [--dir <work-dir>] [--update]
#
# Defaults: --target hibyr3proii, --dir reference (gitignored). Everything is
# built inside the work dir; nothing outside it is modified except Homebrew
# packages. Rockbox is pinned to a tested commit (rockbox_commit in this file);
# --update builds the latest Rockbox instead. If that works, move the pin.
#
# Rockbox's build assumes Linux and GCC. The patch_makefile and gen_headers
# steps in this script make it build with Apple clang; see DEV.md.

set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
target="hibyr3proii"
work="$repo/reference"
update=false
inter_version="4.1"
# Rockbox commit this setup is tested with (2026-10-10)
rockbox_commit="b819e910007795e51bf2a3d429574be7d52c4827"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) target="$2"; shift 2 ;;
    --dir) work="$(mkdir -p "$2" && cd "$2" && pwd)"; shift 2 ;;
    --update) update=true; shift ;;
    -h|--help) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

rb="$work/rockbox"
log="$work/setup.log"
mkdir -p "$work"
: > "$log"

step() { printf '\n==> %s\n' "$*"; }
run() {  # run a command, sending output to the log; show the tail on failure
  if ! "$@" >> "$log" 2>&1; then
    echo "Failed: $*" >&2
    tail -20 "$log" >&2
    echo "Full log: $log" >&2
    exit 1
  fi
}

# ---------------------------------------------------------------- prerequisites
step "Checking prerequisites"
command -v brew > /dev/null || { echo "Homebrew is required: https://brew.sh" >&2; exit 1; }
for tool in cc make perl git curl unzip; do
  command -v "$tool" > /dev/null || { echo "Missing $tool (install Xcode command line tools)" >&2; exit 1; }
done
for pkg in sdl2 freetype pkg-config; do
  brew list "$pkg" > /dev/null 2>&1 || run brew install "$pkg"
done
echo "ok"

# ---------------------------------------------------------------- Rockbox source
step "Rockbox source ($rb)"
if [[ ! -d "$rb/.git" ]]; then
  run git init -q "$rb"
  run git -C "$rb" remote add origin https://github.com/Rockbox/rockbox.git
fi
want="$rockbox_commit"
$update && want="master"
if $update || [[ "$(git -C "$rb" rev-parse HEAD 2> /dev/null)" != "$rockbox_commit" ]]; then
  # undo the test hook so the checkout is clean; it's re-applied below
  git -C "$rb" checkout -q -- firmware/target/hosted/sdl/button-sdl.c 2> /dev/null || true
  run git -C "$rb" fetch --depth 1 origin "$want"
  run git -C "$rb" checkout -q --detach FETCH_HEAD
fi
git -C "$rb" log -1 --format='%h %cd %s' --date=short
if $update && [[ "$(git -C "$rb" rev-parse HEAD)" != "$rockbox_commit" ]]; then
  echo "Building the latest Rockbox. If everything works, set rockbox_commit in tools/setup.sh to:"
  git -C "$rb" rev-parse HEAD
fi

# The simulator test hook replays scripted touches and screenshots (DEV.md).
if git -C "$rb" apply --check "$repo/tools/sim-test-hook.patch" 2> /dev/null; then
  run git -C "$rb" apply "$repo/tools/sim-test-hook.patch"
  echo "applied simulator test hook"
elif git -C "$rb" apply --check -R "$repo/tools/sim-test-hook.patch" 2> /dev/null; then
  echo "simulator test hook already applied"
else
  echo "Warning: the simulator test hook no longer applies to this Rockbox version." >&2
fi

# ---------------------------------------------------------------- convttf
step "convttf"
run cc -O2 -o "$rb/tools/convttf" "$rb/tools/convttf.c" $(pkg-config --cflags --libs freetype2)
echo "$rb/tools/convttf"

# ---------------------------------------------------------------- build helpers
# Point a configured Rockbox Makefile at Apple clang and drop Linux-only flags.
patch_makefile() {
  local mk="$1/Makefile"
  sed -i '' \
    -e 's/^export CC=.*/export CC=cc/' \
    -e 's/^export CPP=.*/export CPP=cc -E/' \
    -e 's/^export AR=.*/export AR=ar/' \
    -e 's/^export GCCOPTS=/export GCCOPTS=-D_FORTIFY_SOURCE=0 -Wno-error -Wno-incompatible-function-pointer-types -Wno-int-conversion /' \
    -e '/^export LDOPTS=/s/-lasound *//; /^export LDOPTS=/s/-lrt *//' \
    -e 's/^export GLOBAL_LDOPTS=.*/export GLOBAL_LDOPTS=/' \
    "$mk"
  # Codecs link with -lgcc, which clang doesn't ship; its runtime covers it.
  mkdir -p "$1/stub"
  echo "" | cc -x c -c -o "$1/stub/empty.o" -
  ar rcs "$1/stub/libgcc.a" "$1/stub/empty.o"
  sed -i '' "s|^export SHARED_LDFLAGS=-dynamiclib|export SHARED_LDFLAGS=-L$1/stub -dynamiclib|" "$mk"
}

# Generated headers that Rockbox's Makefiles don't order correctly.
gen_headers() {
  local dir="$1"; shift
  for header in "$@"; do
    run make -C "$dir" "$dir/$header"
  done
}

configure() {  # configure <build-dir> <type> [extra configure args]
  local dir="$1" type="$2"; shift 2
  rm -rf "$dir"
  mkdir -p "$dir"
  (cd "$dir" && run "$rb/tools/configure" --target="$target" --type="$type" "$@")
  patch_makefile "$dir"
}

# ---------------------------------------------------------------- checkwps
step "checkwps ($target)"
cw="$rb/build-checkwps"
configure "$cw" C --ram=32
gen_headers "$cw" apps/features lang_enum.h lang/max_language_size.h fontbundle.h themeassets.h
run make -C "$cw"
ls "$cw"/checkwps.*

# ---------------------------------------------------------------- simulator
step "Simulator ($target), takes a few minutes"
sim="$rb/build-sim"
configure "$sim" s
gen_headers "$sim" apps/features lang_enum.h lang/max_language_size.h sysfont.h rbversion.h bitmaps/rockboxlogo.h
run make -C "$sim" bin
# Codecs are needed to play music. Some plugins don't build on macOS; that's fine.
make -C "$sim" -k -j"$(sysctl -n hw.ncpu)" build >> "$log" 2>&1 || true
run make -C "$sim" fullinstall
echo "codecs: $(ls "$sim/simdisk/.rockbox/codecs" | wc -l | tr -d ' ')"

step "Test music"
python3 -I "$repo/tools/make-test-music.py" "$sim/simdisk"

# ---------------------------------------------------------------- Inter
step "Inter $inter_version"
inter="$work/inter"
if [[ ! -f "$inter/extras/ttf/Inter-Regular.ttf" ]]; then
  mkdir -p "$inter"
  run curl -fsSL -o "$inter/inter.zip" \
    "https://github.com/rsms/inter/releases/download/v$inter_version/Inter-$inter_version.zip"
  run unzip -o -q "$inter/inter.zip" -d "$inter"
  rm "$inter/inter.zip"
fi
echo "$inter/extras/ttf"

step "Done"
cat <<EOF
checkwps   $cw/checkwps.$target
convttf    $rb/tools/convttf
simulator  ./simulate.sh <device-folder> [theme]
Inter      $inter/extras/ttf
EOF
