"""Tests for bookings snapshot generation."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from notifications.snapshot import build_snapshot, write_snapshot

T1 = "T1 Renovado c/ metro à porta"
EB = "Loft c/ Varanda Solarenga a 5 Minutos Ponte Luíz I"


def _booking(
    listing_name: str,
    start_date: str,
    end_date: str,
    *,
    guest_first_name: str | None = "João",
    status: str = "Aceite",
) -> dict:
    return {
        "listingName": listing_name,
        "startDate": start_date,
        "endDate": end_date,
        "guestFirstName": guest_first_name,
        "status": status,
    }


class TestBuildSnapshot:
    def test_keeps_accepted_bookings_with_slim_fields(self) -> None:
        payload = {
            "extractedAt": "2026-07-05",
            "bookings": [
                _booking(T1, "2026-07-10", "2026-07-15", guest_first_name="Ana"),
                _booking(EB, "2026-07-12", "2026-07-14", guest_first_name=None),
            ],
        }
        snapshot = build_snapshot(payload)
        assert snapshot == {
            "generatedAt": "2026-07-05",
            "bookings": [
                {
                    "listing": "T1",
                    "startDate": "2026-07-10",
                    "endDate": "2026-07-15",
                    "guestFirstName": "Ana",
                },
                {
                    "listing": "EB",
                    "startDate": "2026-07-12",
                    "endDate": "2026-07-14",
                    "guestFirstName": None,
                },
            ],
        }

    def test_skips_unknown_listings_and_non_accepted_status(self) -> None:
        payload = {
            "bookings": [
                _booking("Unknown listing", "2026-07-10", "2026-07-15"),
                _booking(T1, "2026-07-10", "2026-07-15", status="Pendente"),
            ]
        }
        assert build_snapshot(payload) == {
            "generatedAt": date.today().isoformat(),
            "bookings": [],
        }


class TestWriteSnapshot:
    def test_writes_json_file(self, tmp_path: Path) -> None:
        payload = {"bookings": [_booking(T1, "2026-07-10", "2026-07-15")]}
        out = tmp_path / "bookings-snapshot.json"
        write_snapshot(out, payload)
        written = json.loads(out.read_text(encoding="utf-8"))
        assert written["bookings"][0]["listing"] == "T1"
