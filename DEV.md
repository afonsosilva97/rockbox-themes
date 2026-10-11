# Developing themes

How to edit, check and preview themes on a Mac without copying them to the player each time.

## What lives where

| Path | In git | What it is |
|---|---|---|
| `<device>/.rockbox/` | yes | The theme files exactly as they go on the SD card |
| `<device>/src/<theme>/` | yes | Scripts that generate a theme's fonts and bitmaps |
| `<device>/previews/` | yes | HTML previews to share |
| `install.sh` | yes | Copies a device's themes onto a card (or the simulator's card) |
| `simulate.sh` | yes | Opens the simulator with a device's themes |
| `tools/` | yes | Setup and checking scripts |
| `reference/` | no | Local build of Rockbox's tools and simulator, Inter, upstream themes (about 1 GB) |

`reference/` is rebuilt from scratch by `tools/setup.sh`, so it never needs backing up.

## One-time setup

```bash
tools/setup.sh
```

This needs Homebrew and the Xcode command line tools. It installs `sdl2`, `freetype` and `pkg-config` with Homebrew if they're missing, then builds everything into `reference/`:

- **checkwps:** Rockbox's skin checker, built for the HiBy R3 Pro II's 480×720 screen.
- **convttf:** converts TTF fonts to anti-aliased Rockbox `.fnt` files.
- **The UI simulator:** the real Rockbox interface as a Mac app, with codecs and a small silent test library under Files → Music.
- **Inter 4.1:** the font iris-r3 is built from.

The first run takes two to three minutes, depending on the download. Output goes to `reference/setup.log`.

Rockbox is pinned to the commit this setup was tested with (`rockbox_commit` in `tools/setup.sh`), so a later Rockbox change can't break the build unexpectedly.

Options:
- `--update` builds the latest Rockbox instead of the pinned commit. If everything still works (setup, `tools/check.sh`, the simulator), move the pin to the commit it prints.
- `--target <name>` builds for another Rockbox target (e.g. `hibyr1`) when a new device folder is added.
- `--dir <path>` builds somewhere other than `reference/`. Set `THEMES_WORK=<path>` so the other scripts find it.

## Everyday loop

1. Edit the theme in `<device>/.rockbox/`.
2. Check it:
   ```bash
   tools/check.sh hiby-r3proii
   ```
3. Look at it:
   ```bash
   ./simulate.sh hiby-r3proii iris-r3
   ```
4. When it looks right, copy it to the player:
   ```bash
   ./install.sh hiby-r3proii /Volumes/R3PROII
   ```
   Then eject, **restart the player, and select the theme again** in Browse Theme Files. The restart reloads changed skin files and fonts (re-selecting alone doesn't); selecting the theme applies changed `.cfg` settings like the icon set or scrollbar (restarting alone doesn't).

## What needs rebuilding when

| You changed | Do this |
|---|---|
| `.wps`, `.sbs` or `.cfg` | Nothing to build. Rerun `./simulate.sh`, which copies the files again. |
| A theme's bitmaps or fonts (e.g. `src/iris-r3/make_bitmaps.py`) | `hiby-r3proii/src/iris-r3/build.sh`, then `./simulate.sh` |
| Anything visible, before committing | `hiby-r3proii/src/iris-r3/screenshots.sh` to refresh the README screenshots and preview page |
| Rockbox version | `tools/setup.sh --update` |
| Nothing, but the simulator acts strangely | `tools/setup.sh` (rebuilds from scratch) |

The simulator itself never needs rebuilding for theme changes. It reads the theme files from its virtual SD card each time it starts.

## Using the simulator

`./simulate.sh <device> [theme]` merges the device's `.rockbox/` into the simulator's virtual SD card (`reference/rockbox/build-sim/simdisk/`) and opens a window showing the player's screen.

- The mouse acts as your finger: click to tap, hold to long-press, drag to scroll.
- **F5** saves a screenshot to `simdisk/` as `dump <date>.bmp`.
- Naming a theme selects it by copying its `.cfg` over the simulator's settings file. Leave the theme off to keep the simulator's current settings.
- Settings you change in the simulator stay in `simdisk/.rockbox/config.cfg`. They never touch your player.
- Test tracks are under Files → Music: an album with cover art (one title is long enough to scroll) and a track without cover art. They're silent.

### Scripted runs

`tools/setup.sh` patches the simulator (`tools/sim-test-hook.patch`) so it can replay taps and take screenshots by itself:

```bash
cd reference/rockbox/build-sim
RB_TEST_SCRIPT="5000 down 100 110;5100 up;7000 dump;8000 quit" ./rockboxui --nobackground
```

Each step is `<milliseconds since start> <action>`, separated by `;`. Actions are `down <x> <y>`, `up`, `keys <hex>` (hold hardware buttons; `0` releases), `dump` (screenshot) and `quit`. On the R3 Pro II, power is `1` and volume up `10`, so key lock is `keys 1;keys 11;keys 0` a few hundred milliseconds apart. Coordinates are screen pixels. Leave about five seconds for the simulator to start (the first start after a rebuild is the slowest) and a second or two after each tap for the screen to settle. With `--nobackground` the window shows only the screen, so window and screen coordinates match. This is how screens get checked without clicking through them. `hiby-r3proii/src/iris-r3/screenshots.sh` uses it to regenerate iris-r3's screenshots and re-embed them in `previews/iris-r3.html`.

## Rockbox's build on macOS

Rockbox's build expects Linux and GCC. `tools/setup.sh` handles the differences, so this is only for when something breaks after an update:

- The generated Makefiles name versioned GCC tools (`gcc-16`); they're switched to `cc`, `cc -E` and `ar`.
- macOS's `_FORTIFY_SOURCE` macros clash with Rockbox's own `strlcpy`, so it's disabled. A few warnings clang treats as errors are relaxed.
- Linux-only libraries (`-lasound`, `-lrt`) and the `-z defs` linker flag are removed.
- Codecs link against `libgcc`, which clang doesn't have; an empty stub library stands in for it.
- Some generated headers (`lang.h`, `sysfont.h`, `rockboxlogo.h` and others) aren't ordered correctly in the Makefiles, so they're built explicitly first.
- Some plugins don't compile on macOS. They aren't needed for themes.

## Skin engine pitfalls

Things that pass `checkwps` but go wrong on the screen. All of them came up while building iris-r3.

- **Viewports are cleared on a full redraw.** Every visible viewport, apart from the default one, is filled with its background colour in the order it's defined. An invisible touch viewport wipes whatever was drawn before it under the same area. Define touch and background viewports first, then draw over them.
- **Touch regions only work inside their own viewport.** A region larger than its viewport is cut off, and regions in the `.wps` default viewport don't respond. To make a bigger tap target, make the viewport bigger.
- **Base skin (`.sbs`) touch regions don't respond on Now Playing.** Anything you can tap on Now Playing must be in the `.wps`. The `.sbs` and `.wps` redraw independently, so if both draw the same area (iris-r3's header), they must draw the same thing.
- **`%mh` on the R3 Pro II** (no hold switch) is true while Rockbox's key lock is on (power + volume up), in every skin. It's also true, in the `.wps` only, for a skin touch lock set by a `lock` touch action. iris-r3 uses only key lock, so its lock screen and hint match what unlocks it.
- **Don't let two skins draw the same area across a state change.** When the lock lifted, the `.sbs` lock screen and the `.wps` redrew independently and left a half-drawn Now Playing. iris-r3 draws the lock screen only in the `.wps`.
- **Don't hide or cover the menu list from the `.sbs`.** Switching the list viewport (`%VI`) or drawing over it only looks right when something forces a full redraw (e.g. Rockbox's lock notification). Without one, the list stays hidden after unlocking, or the overlay is drawn half over the list. In menus iris-r3 only changes the title bar to LOCKED.
- **List icons carry state, so they can't all be blank.** Rockbox shows on/off in option lists (e.g. Advanced Key Lock), the playing/queued/moving track in the playlist viewer and selected folders only through icons. Rockbox also reuses icon slots across contexts: the "selected" dot is the generic-submenu icon, the audio-file icon marks "Database" in the main menu, and the playlist-file icon marks "Playlists". So file-type icons can't be drawn without putting icons on menu rows; iris-r3 draws only state icons. Icons sit on the selection bar too, so use 32-bit BMPs with alpha and give accent-coloured glyphs a dark halo.
- **Only Rockbox's built-in list scrollbar can be dragged.** A skin-drawn list bar (`%LB`) gets no touch region, so iris-r3 uses `scrollbar: right` in the `.cfg`. Its width is also its grab area, and it's drawn in the list's text colour. It only appears when a list doesn't fit the screen.
- **`list padding` is the total extra row height**, not padding per side. On a 32 px font, 28 gives 60 px rows. It's a global setting, so it stays when switching to a theme that doesn't set it.
- **`statusbar` and `ui viewport`** in a `.cfg` only shape Rockbox's built-in bar, which isn't used when the theme has a `.sbs`.
