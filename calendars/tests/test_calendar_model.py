"""Tests for calendars/calendar_model.py."""

from __future__ import annotations

from datetime import date

from calendars.calendar_model import build_occupied_cells, month_grid
from shared.listing_labels import LISTING_LABELS

T2 = "Totalmente Renovado, metro à porta"


def _booking(
    listing_name: str,
    start_date: str,
    end_date: str,
    *,
    confirmation_code: str = "HMTEST001",
    adults: int = 2,
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


class TestBuildOccupiedCells:
    def test_paints_stay_days_for_known_listing(self) -> None:
        bookings = [_booking(T2, "2026-03-10", "2026-03-12")]
        occupied = build_occupied_cells(2026, bookings)
        label = LISTING_LABELS[T2]

        assert date(2026, 3, 10) in occupied
        assert date(2026, 3, 11) in occupied
        assert date(2026, 3, 12) in occupied
        assert occupied[date(2026, 3, 10)][label].guest_label == "2a"
        assert occupied[date(2026, 3, 11)][label].guest_label == ""

    def test_shows_first_name_on_check_in_day(self) -> None:
        bookings = [
            _booking(T2, "2026-03-10", "2026-03-12", guest_first_name="Jean")
        ]
        occupied = build_occupied_cells(2026, bookings)
        label = LISTING_LABELS[T2]
        assert occupied[date(2026, 3, 10)][label].guest_label == "2a - Jean"
        assert occupied[date(2026, 3, 11)][label].guest_label == ""

    def test_skips_outgoing_checkout_on_same_day_turnover(self) -> None:
        bookings = [
            _booking(T2, "2026-06-01", "2026-06-05", confirmation_code="OUT"),
            _booking(T2, "2026-06-05", "2026-06-10", confirmation_code="IN"),
        ]
        occupied = build_occupied_cells(2026, bookings)
        label = LISTING_LABELS[T2]

        assert occupied[date(2026, 6, 4)][label].confirmation_code == "OUT"
        assert occupied[date(2026, 6, 5)][label].confirmation_code == "IN"

    def test_ignores_unknown_listing(self) -> None:
        bookings = [_booking("Unknown", "2026-01-01", "2026-01-03")]
        assert build_occupied_cells(2026, bookings) == {}


class TestMonthGrid:
    def test_marks_weekend_columns(self) -> None:
        columns = month_grid(2026, 1)
        day_columns = [col for col in columns if col.day is not None]
        assert any(col.is_weekend for col in day_columns)
        assert any(not col.is_weekend for col in day_columns)

    def test_january_2026_has_31_days(self) -> None:
        columns = month_grid(2026, 1)
        day_numbers = [col.day for col in columns if col.day is not None]
        assert day_numbers == list(range(1, 32))
