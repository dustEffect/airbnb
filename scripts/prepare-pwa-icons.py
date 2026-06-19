#!/usr/bin/env python3
"""Composite transparent launcher PNGs onto the PWA splash background.

Android renders transparent pixels as black on the native maskable splash.
Run after copying new art from ~/Downloads/apps (or ~/Downloads/icons):

  python3 scripts/prepare-pwa-icons.py
  # then bump PWA_ASSET_VERSION in shared/pwa.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from shared.pwa import PWA_SPLASH_BACKGROUND

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "icons"
SOURCES = [
    Path.home() / "Downloads" / "apps",
    Path.home() / "Downloads" / "icons",
]

_BG = tuple(int(PWA_SPLASH_BACKGROUND[i : i + 2], 16) for i in (1, 3, 5))


def _source(size: int) -> Path:
    name = f"launchericon-{size}x{size}.png"
    for folder in SOURCES:
        path = folder / name
        if path.is_file():
            return path
    raise FileNotFoundError(f"Missing {name} in {' or '.join(str(s) for s in SOURCES)}")


def flatten_icon(size: int) -> None:
    src = _source(size)
    im = Image.open(src).convert("RGBA")
    if im.size != (size, size):
        im = im.resize((size, size), Image.Resampling.LANCZOS)
    bg = Image.new("RGBA", (size, size), (*_BG, 255))
    out = Image.alpha_composite(bg, im).convert("RGB")
    dst = OUT / f"icon-{size}.png"
    out.save(dst, "PNG", optimize=True)
    print(f"Wrote {dst.relative_to(ROOT)} from {src}")


def main() -> None:
    for size in (192, 512):
        flatten_icon(size)


if __name__ == "__main__":
    main()
