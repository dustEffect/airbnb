"""Tests for calendars/main.py."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from calendars.main import build_calendar_html

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


class TestBuildCalendarHtml:
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

        year, html_path = build_calendar_html(bookings_path, output_dir)
        assert year == 2026
        assert html_path == output_dir / "calendar-2026.html"
        assert html_path.is_file()
        html_text = html_path.read_text(encoding="utf-8")
        assert "Mapa de Estadias 2026" in html_text
        assert "2a" in html_text

    def test_writes_checkouts_summary_and_embeds_saidas(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class FixedDate(date):
            @classmethod
            def today(cls) -> date:
                return cls(2026, 6, 9)

        monkeypatch.setattr("checkouts.checkouts_format.date", FixedDate)
        monkeypatch.setattr("shared.paths.project_root", lambda: tmp_path)
        bookings_path = tmp_path / "shared" / "bookings.json"
        output_dir = tmp_path / "out"
        bookings_path.parent.mkdir(parents=True)
        bookings_path.write_text(
            json.dumps(
                {
                    "dateRange": {
                        "startDate": "2026-01-01",
                        "endDate": "2026-12-31",
                    },
                    "bookings": [
                        _booking(T2, "2026-06-01", "2026-06-08"),
                        _booking(T2, "2026-06-10", "2026-06-14"),
                    ],
                }
            ),
            encoding="utf-8",
        )

        _, html_path = build_calendar_html(bookings_path, output_dir)

        checkouts_path = tmp_path / "checkouts" / "checkouts.txt"
        assert checkouts_path.is_file()
        assert "8 seg. T2" in checkouts_path.read_text(encoding="utf-8")
        html_text = html_path.read_text(encoding="utf-8")
        assert 'id="saidas-backdrop"' in html_text
        assert "14 dom. T2" in html_text
        assert "8 seg. T2" not in html_text
