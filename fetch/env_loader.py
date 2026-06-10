"""Load variables from `credentials.local.env` at the project root."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from shared.paths import project_root


def load_credentials_env(root: Path | None = None, *, override: bool = True) -> Path | None:
    """
    Read `credentials.local.env` and set values in `os.environ`.

    With `override=True`, file values take precedence over variables already set in the shell.
    Returns the file path if it exists; otherwise None.
    """
    base = root or project_root()
    path = base / "credentials.local.env"
    if path.is_file():
        load_dotenv(path, override=override)
        return path
    return None


def get_airbnb_credentials() -> tuple[str, str]:
    """Read AIRBNB_EMAIL and AIRBNB_PASSWORD from the environment (loads .env via `load_credentials_env` first)."""
    email = (os.environ.get("AIRBNB_EMAIL") or "").strip()
    password = os.environ.get("AIRBNB_PASSWORD")
    if password is None:
        password = ""
    if not email:
        raise ValueError(
            "Missing AIRBNB_EMAIL in credentials.local.env (or in the environment)."
        )
    if not password:
        raise ValueError(
            "Missing AIRBNB_PASSWORD in credentials.local.env (or in the environment)."
        )
    return email, password
