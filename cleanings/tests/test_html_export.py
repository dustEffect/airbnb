"""Tests for cleanings/html_export.py."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from cleanings.calendar_model import LISTING_ROW_ORDER
from cleanings.html_export import (
    _initial_month_section_id,
    render_cleaning_html,
    stay_cell_id,
    weekday_header_id,
    write_cleaning_html,
)
from cleanings.booking_helpers import MONTHS_PT

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

        assert "Mapa de Estadias 2026" in html_text
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

    def test_weekday_header_ids_are_unique_per_year_month_and_column(self) -> None:
        assert weekday_header_id(2026, 1, 7) == "ac-wh-2026-01-c07"
        assert weekday_header_id(2027, 3, 12) == "ac-wh-2027-03-c12"

    def test_weekday_headers_cycle_icons_and_persist_state(self) -> None:
        html_text = render_cleaning_html(year=2026, bookings=[])
        assert 'id="ac-wh-2026-01-c04"' in html_text
        assert "airbnb-cleanings-weekday-icons-2026" in html_text
        assert (
            'id="ac-wh-2026-01-c04" class="cell header weekday-header"'
            in html_text
        )
        assert "PLANE_ICON" in html_text
        assert "PALM_ICON" in html_text
        assert "SPONGE_ICON" in html_text
        assert "BUCKET_ICON" not in html_text
        assert "loadWeekdayIcons" in html_text
        assert "persistWeekdayIconState" in html_text
        assert "applySavedWeekdayIcons" in html_text
        assert 'setWeekdayIcon(cell, "plane")' in html_text
        assert 'setWeekdayIcon(cell, "palm")' in html_text
        assert 'setWeekdayIcon(cell, "sponge")' in html_text
        assert "dblclick" in html_text

    def test_commented_cells_have_clear_marker_styles(self) -> None:
        html_text = render_cleaning_html(year=2026, bookings=[])
        assert ".cell.stay-comment.has-comment" in html_text
        assert "dashed" in html_text
        assert "Nota:" in html_text

    def test_long_press_shows_transient_comment_peek(self) -> None:
        html_text = render_cleaning_html(year=2026, bookings=[])
        assert "comment-peek" in html_text
        assert "showCommentPeek" in html_text
        assert "hideCommentPeek" in html_text
        assert "bindLongPress" in html_text
        assert 'id="comment-peek-text"' in html_text
        assert "comment-view-backdrop" not in html_text
        assert "Comentário de limpeza" not in html_text
        assert "limpezas" not in html_text.lower()

    def test_empty_slots_support_custom_stay_selection(self) -> None:
        html_text = render_cleaning_html(year=2026, bookings=[])
        assert 'class="cell listing-row empty-slot' in html_text
        assert 'data-listing="T2"' in html_text
        assert 'id="custom-stay-add"' in html_text
        assert "createCustomStay" in html_text
        assert "airbnb-custom-stays-2026" in html_text
        assert "stay-custom-label" in html_text
        assert ".cell.stay-custom-start .stay-custom-label" in html_text
        assert "customStayHasComment" in html_text

    def test_tooltips_exclude_confirmation_codes(self) -> None:
        bookings = [_booking(T2, "2026-03-10", "2026-03-12")]
        html_text = render_cleaning_html(year=2026, bookings=bookings)
        assert "Reserva:" not in html_text
        assert "HMTEST001" not in html_text
        assert 'title="T2: 2026-03-10 → 2026-03-12 | Hóspedes: 2a"' in html_text

    def test_marks_portugal_national_holidays_on_weekday_headers(self) -> None:
        html_text = render_cleaning_html(year=2026, bookings=[])
        assert "Feriado nacional</span>" in html_text
        assert 'class="cell header weekday-header has-holiday' in html_text
        assert '<span class="holiday-marker" aria-hidden="true">🇵🇹</span>' in html_text
        january = html_text.split('id="janeiro"')[1].split("</section>")[0]
        ano_novo_header = next(
            line for line in january.splitlines() if "has-holiday" in line and "Ano Novo" in line
        )
        assert "weekday-letter" not in ano_novo_header
        assert "holiday-marker" in ano_novo_header
        assert "has-holiday" in ano_novo_header
        assert "--holiday-bg: #D4A017" in html_text
        assert "holiday-day" not in html_text
        assert 'title="Feriado: Ano Novo"' in html_text
        assert 'title="Feriado: Sexta-feira Santa"' in html_text
        assert "national-holiday" not in html_text

    def test_month_grids_align_weekdays_without_padding_cells(self) -> None:
        html_text = render_cleaning_html(year=2026, bookings=[])
        assert 'grid-template-columns: 2.5rem repeat(37, var(--day-size))' in html_text
        weekday_headers = [
            line
            for line in html_text.splitlines()
            if "weekday-header" in line and "data-default=" in line
        ]
        assert len(weekday_headers) == 37 * 12
        assert html_text.count('class="cell day-num') == 365
        january = html_text.split('id="janeiro"')[1].split("</section>")[0]
        assert january.count('class="cell day-num') == 31
        assert 'grid-row:2;grid-column:5">1</div>' in january

    def test_includes_mobile_friendly_viewport_and_layout(self) -> None:
        html_text = render_cleaning_html(year=2026, bookings=[])
        assert "viewport-fit=cover" in html_text
        assert "safe-area-inset" in html_text
        assert "Deslize para ver mais dias" in html_text
        assert "position: sticky" in html_text

    def test_scrolls_to_current_month_on_load(self) -> None:
        year = date.today().year
        html_text = render_cleaning_html(year=year, bookings=[])
        initial_month_id = _initial_month_section_id(year)
        assert f"getElementById({initial_month_id!r})" in html_text
        assert "scrollToInitialMonth" in html_text
        assert "scroll-margin-top" in html_text

    def test_write_cleaning_html_creates_file(self, tmp_path: Path) -> None:
        out = tmp_path / "cleanings-2026.html"
        bookings = [_booking(T2, "2026-03-10", "2026-03-12")]
        write_cleaning_html(year=2026, bookings=bookings, output_path=out)
        assert out.is_file()
        assert "2026" in out.read_text(encoding="utf-8")
