"""Tests for calendars/html_export.py."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from calendars.calendar_model import LISTING_ROW_ORDER
from calendars.html_export import (
    day_cell_id,
    render_calendar_html,
    stay_cell_id,
    weekday_header_id,
    write_calendar_html,
)
from calendars.booking_helpers import MONTHS_PT

T2 = "Totalmente Renovado, metro à porta"


def _booking(
    listing_name: str,
    start_date: str,
    end_date: str,
    *,
    adults: int = 2,
    confirmation_code: str = "HMTEST001",
    guest_first_name: str | None = None,
) -> dict:
    booking = {
        "confirmationCode": confirmation_code,
        "listingName": listing_name,
        "startDate": start_date,
        "endDate": end_date,
        "numberOfAdults": adults,
        "numberOfChildren": 0,
        "numberOfInfants": 0,
    }
    if guest_first_name is not None:
        booking["guestFirstName"] = guest_first_name
    return booking


class TestRenderCalendarHtml:
    def test_includes_year_listings_and_months(self) -> None:
        bookings = [_booking(T2, "2026-03-10", "2026-03-12")]
        html_text = render_calendar_html(year=2026, bookings=bookings)

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
        html_text = render_calendar_html(year=2026, bookings=bookings)
        assert html_text.count('class="cell listing-row stay stay-comment"') == 2
        assert (
            html_text.count('class="cell listing-row stay stay-comment stay-end"') == 1
        )
        assert 'id="T2-20260312" class="cell listing-row stay stay-comment stay-end"' in html_text
        assert 'id="T2-20260310"' in html_text
        assert 'id="T2-20260311"' in html_text
        assert 'id="T2-20260312"' in html_text
        assert ".cell.stay.stay-end" in html_text

    def test_stay_end_gradient_uses_weekend_empty_color_on_weekends(self) -> None:
        bookings = [_booking(T2, "2026-03-12", "2026-03-14")]
        html_text = render_calendar_html(year=2026, bookings=bookings)
        assert 'id="T2-20260312" class="cell listing-row stay stay-comment"' in html_text
        assert (
            'id="T2-20260314" class="cell listing-row stay stay-comment stay-end weekend-end"'
            in html_text
        )
        assert "var(--empty-bg)" in html_text
        assert "border-right-color: var(--border)" in html_text
        assert ".weekend-end" in html_text

    def test_stay_end_gradient_on_last_day_of_each_stay(self) -> None:
        bookings = [
            _booking(T2, "2026-03-10", "2026-03-12", confirmation_code="HMTEST001"),
            _booking(T2, "2026-03-13", "2026-03-15", confirmation_code="HMTEST002"),
        ]
        html_text = render_calendar_html(year=2026, bookings=bookings)
        assert 'id="T2-20260312" class="cell listing-row stay stay-comment stay-end"' in html_text
        assert (
            'id="T2-20260315" class="cell listing-row stay stay-comment stay-end weekend-end"'
            in html_text
        )
        assert "refreshStayEndGradients" in html_text

    def test_weekday_header_ids_are_unique_per_year_month_and_column(self) -> None:
        assert weekday_header_id(2026, 1, 7) == "ac-wh-2026-01-c07"
        assert weekday_header_id(2027, 3, 12) == "ac-wh-2027-03-c12"

    def test_weekday_headers_cycle_icons_and_persist_state(self) -> None:
        html_text = render_calendar_html(year=2026, bookings=[])
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

    def test_marks_today_with_red_circle_on_day_number(self) -> None:
        html_text = render_calendar_html(year=date.today().year, bookings=[])
        assert ".cell.day-num.is-today::before" in html_text
        assert "markToday" in html_text
        assert ' class="cell day-num day-comment is-today"' not in html_text

    def test_scrolls_today_into_center_on_narrow_viewports(self) -> None:
        html_text = render_calendar_html(year=date.today().year, bookings=[])
        assert "scrollTodayIntoCenter" in html_text
        assert 'matchMedia("(max-width: 768px)")' in html_text
        assert "runInitialScroll" in html_text

    def test_scroll_today_button_returns_to_current_day(self) -> None:
        html_text = render_calendar_html(year=date.today().year, bookings=[])
        assert 'id="scroll-today-btn"' in html_text
        assert "goToToday" in html_text
        assert "centerTodayHorizontally" in html_text
        assert 'aria-label="Ir para hoje"' in html_text

    def test_day_number_cells_support_comments(self) -> None:
        html_text = render_calendar_html(year=2026, bookings=[])
        assert day_cell_id(date(2026, 3, 15)) == "dia-20260315"
        assert 'id="dia-20260315"' in html_text
        assert 'class="cell day-num day-comment"' in html_text
        assert "initCommentCells" in html_text

    def test_commented_cells_have_clear_marker_styles(self) -> None:
        html_text = render_calendar_html(year=2026, bookings=[])
        assert ".cell.stay-comment.has-comment" in html_text
        assert ".cell.day-comment.has-comment" in html_text
        assert "dashed" in html_text
        assert ".cell.stay-comment.has-comment::after" in html_text
        assert "Nota:" in html_text

    def test_long_press_shows_transient_comment_peek(self) -> None:
        html_text = render_calendar_html(year=2026, bookings=[])
        assert "comment-peek" in html_text
        assert "showCommentPeek" in html_text
        assert "hideCommentPeek" in html_text
        assert "bindLongPress" in html_text
        assert 'id="comment-peek-text"' in html_text
        assert "comment-view-backdrop" not in html_text
        assert "Comentário de limpeza" not in html_text
        assert "limpezas" not in html_text.lower()

    def test_empty_slots_support_custom_stay_selection(self) -> None:
        html_text = render_calendar_html(year=2026, bookings=[])
        assert 'class="cell listing-row empty-slot' in html_text
        assert 'data-listing="T2"' in html_text
        assert 'id="custom-stay-add"' in html_text
        assert "createCustomStay" in html_text
        assert "toggleEmptySlotSelection" in html_text
        assert "bindEmptySlotLongPress" in html_text
        assert "airbnb-custom-stays-2026" in html_text
        assert "stay-label-mask" in html_text
        assert "layoutStayLabelMask" in html_text
        assert "layoutAirbnbStayLabels" in html_text
        assert "repeating-linear-gradient" in html_text
        assert "customStayHasComment" in html_text

    def test_tooltips_exclude_confirmation_codes(self) -> None:
        bookings = [_booking(T2, "2026-03-10", "2026-03-12")]
        html_text = render_calendar_html(year=2026, bookings=bookings)
        assert "Reserva:" not in html_text
        assert 'title="T2: 2026-03-10 → 2026-03-12 | Hóspedes: 2a"' in html_text
        assert 'data-stay-key="HMTEST001"' in html_text

    def test_guest_display_label_uses_spanning_mask_not_inline_text(self) -> None:
        bookings = [_booking(T2, "2026-03-10", "2026-03-12", guest_first_name="Jean")]
        html_text = render_calendar_html(year=2026, bookings=bookings)
        assert 'data-guest-label="2a - Jean"' in html_text
        assert not re.search(r'id="T2-20260310"[^>]*>2a - Jean</div>', html_text)
        assert 'title="T2: 2026-03-10 → 2026-03-12 | Hóspedes: 2a - Jean"' in html_text
        assert "getBoundingClientRect" in html_text
        assert "layoutStayLabelMask" in html_text
        assert (
            "if (!label || cells.length === 0) return;\n    removeStayLabelMask(maskKey);"
            in html_text
        )

    def test_long_press_opens_airbnb_stay_url(self) -> None:
        html_text = render_calendar_html(
            year=2026,
            bookings=[_booking(T2, "2026-03-10", "2026-03-12", confirmation_code="HMEST3TFBZ")],
        )
        assert "airbnbReservationUrlForCell" in html_text
        assert "https://www.airbnb.pt/hosting/stay/" in html_text
        assert 'data-stay-key="HMEST3TFBZ"' in html_text
        assert "window.open(stayUrl" in html_text

    def test_marks_portugal_national_holidays_on_weekday_headers(self) -> None:
        html_text = render_calendar_html(year=2026, bookings=[])
        assert "Feriado nacional</span>" not in html_text
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
        html_text = render_calendar_html(year=2026, bookings=[])
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
        assert 'id="dia-20260101"' in january
        assert 'grid-row:2;grid-column:5" data-date="20260101" role="button" tabindex="0">1</div>' in january

    def test_listing_labels_match_stay_row_height(self) -> None:
        html_text = render_calendar_html(year=2026, bookings=[])
        assert ".cell.listing-label.listing-label-row" in html_text
        assert 'class="cell listing-label listing-label-row"' in html_text
        assert 'grid-row:1;grid-column:1"></div>' not in html_text
        assert ">dia</div>" not in html_text

    def test_includes_mobile_friendly_viewport_and_layout(self) -> None:
        html_text = render_calendar_html(year=2026, bookings=[])
        assert "viewport-fit=cover" in html_text
        assert "safe-area-inset" in html_text
        assert "Deslize para ver mais dias" in html_text
        assert "position: sticky" in html_text

    def test_includes_pwa_manifest_and_service_worker(self) -> None:
        html_text = render_calendar_html(year=2026, bookings=[])
        assert 'rel="manifest" href="/airbnb/manifest.webmanifest?v=8"' in html_text
        assert "navigator.serviceWorker.register('/airbnb/sw.js?v=8'" in html_text
        assert "updateViaCache: \"none\"" in html_text
        assert 'scope: "/airbnb/"' in html_text
        assert 'name="apple-mobile-web-app-capable"' in html_text
        assert 'href="/airbnb/icons/icon-192.png?v=8" sizes="192x192"' in html_text
        assert 'href="/airbnb/icons/icon-512.png?v=8" sizes="512x512"' in html_text
        assert 'name="theme-color" content="#D7EBFA"' in html_text

    def test_includes_push_subscribe_controls(self) -> None:
        html_text = render_calendar_html(year=2026, bookings=[])
        assert "Ativar notificações" in html_text
        assert "push-subscribe-btn" in html_text
        assert "VAPID_PUBLIC_KEY" in html_text

    def test_disables_push_subscribe_when_vapid_key_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("VAPID_PUBLIC_KEY", raising=False)
        html_text = render_calendar_html(year=2026, bookings=[])
        assert "Notificações não configuradas" in html_text

    def test_scrolls_to_current_month_on_load(self) -> None:
        html_text = render_calendar_html(year=date.today().year, bookings=[])
        assert "MONTH_IDS" in html_text
        assert "now.getMonth()" in html_text
        assert "getElementById(MONTH_IDS[monthIndex])" in html_text
        assert "scrollToInitialMonth" in html_text
        assert "scroll-margin-top" in html_text

    def test_write_calendar_html_creates_file(self, tmp_path: Path) -> None:
        out = tmp_path / "calendar-2026.html"
        bookings = [_booking(T2, "2026-03-10", "2026-03-12")]
        write_calendar_html(year=2026, bookings=bookings, output_path=out)
        assert out.is_file()
        assert "2026" in out.read_text(encoding="utf-8")


class TestSaidasModal:
    def test_embeds_upcoming_checkout_summary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class FixedDate(date):
            @classmethod
            def today(cls) -> date:
                return cls(2026, 6, 9)

        monkeypatch.setattr("checkouts.checkouts_format.date", FixedDate)
        bookings = [
            _booking(T2, "2026-06-01", "2026-06-08"),
            _booking(T2, "2026-06-10", "2026-06-14"),
        ]
        html_text = render_calendar_html(year=2026, bookings=bookings)

        assert 'id="saidas-backdrop"' in html_text
        assert 'id="saidas-title">Saídas</h3>' in html_text
        assert "14 dom. T2" in html_text
        assert "8 seg. T2" not in html_text
        assert 'id="page-title-btn"' in html_text
        assert 'addEventListener("click", openSaidasDialog)' in html_text

    def test_shows_empty_message_when_no_upcoming_checkouts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class FixedDate(date):
            @classmethod
            def today(cls) -> date:
                return cls(2026, 6, 9)

        monkeypatch.setattr("checkouts.checkouts_format.date", FixedDate)
        bookings = [_booking(T2, "2026-06-01", "2026-06-08")]
        html_text = render_calendar_html(year=2026, bookings=bookings)

        assert "Sem saídas agendadas." in html_text
        assert "8 seg. T2" not in html_text
