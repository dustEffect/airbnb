"""Repository layout paths shared across pipelines."""

from __future__ import annotations

from pathlib import Path

SHARED_DIR = "shared"
CHECKOUTS_DIR = "checkouts"
CALENDARS_DIR = "calendars"
BOOKINGS_FILENAME = "bookings.json"
BOOKINGS_SNAPSHOT_FILENAME = "bookings-snapshot.json"
CHECKOUTS_SUMMARY_FILENAME = "checkouts.txt"


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def bookings_json_path(root: Path | None = None) -> Path:
    return (root or project_root()) / SHARED_DIR / BOOKINGS_FILENAME


def checkouts_summary_path(root: Path | None = None) -> Path:
    return (root or project_root()) / CHECKOUTS_DIR / CHECKOUTS_SUMMARY_FILENAME


def bookings_snapshot_path(root: Path | None = None) -> Path:
    return (root or project_root()) / "docs" / BOOKINGS_SNAPSHOT_FILENAME
