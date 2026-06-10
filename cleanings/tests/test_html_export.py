"""Tests for cleanings/html_export.py."""

from __future__ import annotations

from pathlib import Path

from cleanings.calendar_model import LISTING_ROW_ORDER
from cleanings.html_export import render_cleaning_html, stay_cell_id, write_cleaning_html
from cleanings.main import MONTHS_PT

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


class TestRenderCleaningHtml:
    def test_includes_year_listings_and_months(self) -> None:
        bookings = [_booking(T2, "2026-03-10", "2026-03-12")]
        html_text = render_cleaning_html(year=2026, bookings=bookings)

        assert "Calendário de limpezas 2026" in html_text
        for label in LISTING_ROW_ORDER:
            assert label in html_text
        for month in MONTHS_PT:
            assert month in html_text
        assert "2a" in html_text
        assert 'id="T2-20260310"' in html_text
        assert "stay-comment" in html_text
        assert "airbnb-cleanings-comments-2026" in html_text
        assert stay_cell_id("T2", __import__("datetime").date(2026, 3, 10)) == "T2-20260310"

    def test_all_stay_day_cells_are_clickable(self) -> None:
        bookings = [_booking(T2, "2026-03-10", "2026-03-12")]
        html_text = render_cleaning_html(year=2026, bookings=bookings)
        assert html_text.count('class="cell listing-row stay stay-comment"') == 3
        assert 'id="T2-20260310"' in html_text
        assert 'id="T2-20260311"' in html_text
        assert 'id="T2-20260312"' in html_text

    def test_weekday_headers_support_palm_toggle(self) -> None:
        html_text = render_cleaning_html(year=2026, bookings=[])
        assert 'class="cell header weekday-header" data-default="S">S</div>' in html_text
        assert "PALM_ICON" in html_text
        assert "dblclick" in html_text

    def test_commented_cells_have_clear_marker_styles(self) -> None:
        html_text = render_cleaning_html(year=2026, bookings=[])
        assert ".cell.stay-comment.has-comment" in html_text
        assert "dashed" in html_text
        assert "Nota:" in html_text

    def test_tooltips_exclude_confirmation_codes(self) -> None:
        bookings = [_booking(T2, "2026-03-10", "2026-03-12")]
        html_text = render_cleaning_html(year=2026, bookings=bookings)
        assert "Reserva:" not in html_text
        assert "HMTEST001" not in html_text
        assert 'title="T2: 2026-03-10 → 2026-03-12 | Hóspedes: 2a"' in html_text

    def test_includes_mobile_friendly_viewport_and_layout(self) -> None:
        html_text = render_cleaning_html(year=2026, bookings=[])
        assert "viewport-fit=cover" in html_text
        assert "safe-area-inset" in html_text
        assert "Deslize para ver mais dias" in html_text
        assert "position: sticky" in html_text

    def test_write_cleaning_html_creates_file(self, tmp_path: Path) -> None:
        out = tmp_path / "cleanings-2026.html"
        bookings = [_booking(T2, "2026-03-10", "2026-03-12")]
        write_cleaning_html(year=2026, bookings=bookings, output_path=out)
        assert out.is_file()
        assert "2026" in out.read_text(encoding="utf-8")
