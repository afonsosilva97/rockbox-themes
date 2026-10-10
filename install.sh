#!/usr/bin/env bash
#
# Merge a device folder's .rockbox/ onto a mounted Rockbox SD card.
#
#   ./install.sh <device-folder> <card-path> [--dry-run]
#
# Never deletes anything on the card. Files removed from the repo stay on the
# card until deleted by hand.

set -euo pipefail

usage() {
  echo "Usage: $0 <device-folder> <card-path> [--dry-run]" >&2
  echo "  e.g. $0 hiby-r3proii /Volumes/R3PROII" >&2
  echo "       $0 hiby-r3proii /Volumes/R3PROII --dry-run" >&2
  exit 1
}

dry_run=false
args=()
for arg in "$@"; do
  case "$arg" in
    --dry-run) dry_run=true ;;
    -h|--help) usage ;;
    -*) echo "Unknown option: $arg" >&2; usage ;;
    *) args+=("$arg") ;;
  esac
done

[[ ${#args[@]} -eq 2 ]] || usage

device="${args[0]%/}"
card="${args[1]%/}"

src="$device/.rockbox"
dest="$card/.rockbox"

if [[ ! -d "$src" ]]; then
  echo "Error: '$src' not found. Is '$device' a device folder in this repo?" >&2
  exit 1
fi

if [[ ! -d "$card" ]]; then
  echo "Error: '$card' not found. Is the SD card mounted? (check: ls /Volumes)" >&2
  exit 1
fi

if [[ ! -d "$dest" ]]; then
  echo "Error: '$dest' not found. Rockbox doesn't seem to be installed on this card." >&2
  exit 1
fi

# Placeholder and macOS metadata files that must not reach the card.
excludes=(--exclude .gitkeep --exclude .DS_Store --exclude '._*')

if $dry_run; then
  echo "Dry run: would merge $src -> $dest"
  (cd "$src" && find . -type f ! -name .gitkeep ! -name .DS_Store ! -name '._*' | sed 's|^\./||' | sort) |
    while IFS= read -r f; do
      if [[ -e "$dest/$f" ]]; then echo "  update  $f"; else echo "  add     $f"; fi
    done
  exit 0
fi

# Stage a filtered copy locally, then merge it onto the card with ditto.
staging="$(mktemp -d)"
trap 'rm -rf "$staging"' EXIT
rsync -a "${excludes[@]}" "$src/" "$staging/"

echo "Merging $src -> $dest"
ditto --norsrc "$staging" "$dest"

dot_clean -m "$card"

echo "Theme files now on the card ($dest/themes):"
ls "$dest/themes"
