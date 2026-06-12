"""Tests for cleanings/main.py."""

from __future__ import annotations

import json
from pathlib import Path

from cleanings.main import build_cleaning_html

T2 = "Totalmente Renovado, metro à porta"


def _booking(
    listing_name: str,
    start_date: str,
    end_date: str,
    *,
    adults: int = 2,
) -> dict:
    return {
        "confirmationCode": "HMTEST001",
        "listingName": listing_name,
        "startDate": start_date,
        "endDate": end_date,
        "numberOfAdults": adults,
        "numberOfChildren": 0,
        "numberOfInfants": 0,
    }


class TestBuildCleaningHtml:
    def test_writes_html_for_booking_year(self, tmp_path: Path) -> None:
        bookings_path = tmp_path / "bookings.json"
        output_dir = tmp_path / "out"
        bookings_path.write_text(
            json.dumps(
                {
                    "dateRange": {
                        "startDate": "2026-01-01",
                        "endDate": "2026-12-31",
                    },
                    "bookings": [
                        _booking(T2, "2026-03-10", "2026-03-14"),
                    ],
                }
            ),
            encoding="utf-8",
        )

        year, html_path = build_cleaning_html(bookings_path, output_dir)
        assert year == 2026
        assert html_path == output_dir / "cleanings-2026.html"
        assert html_path.is_file()
        html_text = html_path.read_text(encoding="utf-8")
        assert "Mapa de Estadias 2026" in html_text
        assert "2a" in html_text
