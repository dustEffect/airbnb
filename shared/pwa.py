"""PWA manifest and asset URLs (shared by HTML export and GitHub Pages)."""

from __future__ import annotations

import json
from pathlib import Path

# Bump when icons or manifest splash metadata change (cache-busts URLs).
PWA_ASSET_VERSION = "5"
PWA_SW_VERSION = "5"

PWA_MANIFEST_PATH = "/airbnb/manifest.webmanifest"
PWA_SCOPE = "/airbnb/"
# Sampled from icon-512.png background (215, 235, 250).
PWA_SPLASH_BACKGROUND = "#D7EBFA"


def pwa_icon_url(size: int) -> str:
    return f"/airbnb/icons/icon-{size}.png?v={PWA_ASSET_VERSION}"


def pwa_manifest_url() -> str:
    return f"{PWA_MANIFEST_PATH}?v={PWA_ASSET_VERSION}"


def pwa_sw_url() -> str:
    return f"/airbnb/sw.js?v={PWA_SW_VERSION}"


def render_web_manifest() -> str:
    manifest = {
        "name": "Mapa de Estadias",
        "short_name": "Estadias",
        "description": "Calendário de estadias e limpezas Airbnb",
        "start_url": PWA_SCOPE,
        "scope": PWA_SCOPE,
        "display": "standalone",
        "background_color": PWA_SPLASH_BACKGROUND,
        "theme_color": PWA_SPLASH_BACKGROUND,
        "lang": "pt",
        "icons": [
            {
                "src": pwa_icon_url(192),
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "maskable",
            },
            {
                "src": pwa_icon_url(512),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
    }
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def write_web_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_web_manifest(), encoding="utf-8")
