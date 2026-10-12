#!/usr/bin/env python3
"""Write the adwaitapod-r3 skins and theme files for both variants.

Usage: python3 make_skins.py <device-folder>/.rockbox

Fills adwaitapod-r3.{wps,sbs,cfg}.in with each variant's colours (variants.py).
Edit the templates, not the generated files.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from variants import VARIANTS  # noqa: E402

TITLES = {"adwaitapod-r3": "Adwaitapod R3 (light)", "adwaitapod-r3-dark": "Adwaitapod R3 (dark)"}
OUTPUTS = {"wps": "wps/{}.wps", "sbs": "wps/{}.sbs", "cfg": "themes/{}.cfg"}


def main(rockbox):
    here = os.path.dirname(os.path.abspath(__file__))
    for theme, v in VARIANTS.items():
        values = {k: "%02x%02x%02x" % c for k, c in v.items() if isinstance(c, tuple) and len(c) == 3}
        values.update(theme=theme, title=TITLES[theme])
        for ext, out in OUTPUTS.items():
            with open(os.path.join(here, f"adwaitapod-r3.{ext}.in")) as f:
                text = f.read().format_map(values)
            path = os.path.join(rockbox, out.format(theme))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(text)
            print(path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
