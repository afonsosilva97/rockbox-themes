# rockbox-themes

Custom [Rockbox](https://www.rockbox.org/) themes, organised per device.

| Device | Screen | Folder |
|---|---|---|
| HiBy R3 Pro II | 480 × 720 portrait, touch | [`hiby-r3proii/`](hiby-r3proii/) |

Themes are in progress. Screenshots will be added under each device's `screenshots/` folder.

## Install

Requirements: macOS, a player with Rockbox already installed, and its SD card mounted. Both arguments are required: the device folder and the card's mount point (check with `ls /Volumes`).

```bash
./install.sh hiby-r3proii /Volumes/R3PROII            # install
./install.sh hiby-r3proii /Volumes/R3PROII --dry-run  # list what would be copied
```

The script merges the device's `.rockbox/` folder into the card's `.rockbox/` with `ditto --norsrc`, then runs `dot_clean` to remove macOS `._*` files. It never deletes anything on the card and never touches Rockbox's built-in themes or your `config.cfg`.

**Note:** because it only merges, files removed or renamed in this repo are not removed from the card. Delete stale files on the card by hand if needed.

Then eject the card, put it in the player and go to **Settings → Theme Settings → Browse Theme Files** to select a theme. If a theme breaks the UI, select `cabbiev2` or `rockbox_failsafe` there to recover.

## Layout

Each device folder contains:

- `.rockbox/`: exactly what gets copied onto the card (`themes/`, `wps/`, `backdrops/`, `icons/`, `fonts/`)
- `src/`: editable source art, not deployed
- `screenshots/`: images for this README

Every file belonging to a theme starts with the theme's name, so several themes can coexist.

## Credits and licence

Adapted themes and their original licences are listed in [CREDITS.md](CREDITS.md). Original work in this repo is licensed as described in [LICENSE](LICENSE).
