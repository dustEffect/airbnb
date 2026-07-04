"""Tests for calendars/booking_helpers.py."""

from __future__ import annotations

from calendars.booking_helpers import (
    booking_listing_label,
    outgoing_same_day_checkout_codes,
    start_column_for_month,
    stay_guest_display_label,
    stay_guest_label,
    year_from_bookings,
    FIRST_DAY_COL,
    TEMPLATE_WEEKDAY_PHASE,
)
from shared.listing_labels import LISTING_LABELS

T2 = "Totalmente Renovado, metro à porta"


def _booking(
    listing_name: str,
    start_date: str,
    end_date: str,
    *,
    confirmation_code: str = "HMTEST001",
    adults: int = 2,
) -> dict:
    return {
        "confirmationCode": confirmation_code,
        "listingName": listing_name,
        "startDate": start_date,
        "endDate": end_date,
        "numberOfAdults": adults,
        "numberOfChildren": 0,
        "numberOfInfants": 0,
    }


class TestYearFromBookings:
    def test_reads_year_from_date_range(self) -> None:
        data = {"dateRange": {"startDate": "2026-01-01", "endDate": "2026-12-31"}}
        assert year_from_bookings(data) == 2026


class TestBookingListingLabel:
    def test_maps_known_listing_name(self) -> None:
        booking = _booking(T2, "2026-06-01", "2026-06-05")
        assert booking_listing_label(booking) == LISTING_LABELS[T2]

    def test_returns_none_for_unknown_listing(self) -> None:
        booking = _booking("Unknown listing", "2026-06-01", "2026-06-05")
        assert booking_listing_label(booking) is None


class TestStayGuestLabel:
    def test_formats_adults_children_infants(self) -> None:
        booking = {
            "numberOfAdults": 2,
            "numberOfChildren": 1,
            "numberOfInfants": 1,
        }
        assert stay_guest_label(booking) == "2a 1c 1b"

    def test_omits_zero_counts(self) -> None:
        assert stay_guest_label({"numberOfAdults": 1}) == "1a"


class TestStayGuestDisplayLabel:
    def test_appends_first_name_after_counts(self) -> None:
        booking = {"numberOfAdults": 2, "guestFirstName": "Jean"}
        assert stay_guest_display_label(booking) == "2a - Jean"

    def test_falls_back_to_counts_without_first_name(self) -> None:
        assert stay_guest_display_label({"numberOfAdults": 3}) == "3a"

    def test_includes_children_and_infants_with_name(self) -> None:
        booking = {
            "numberOfAdults": 2,
            "numberOfChildren": 1,
            "numberOfInfants": 1,
            "guestFirstName": "Marie",
        }
        assert stay_guest_display_label(booking) == "2a 1c 1b - Marie"


class TestStartColumnForMonth:
    def test_january_2026_starts_on_thursday_column(self) -> None:
        # 2026-01-01 is Thursday; phase 0 => column D is Monday
        assert start_column_for_month(2026, 1, TEMPLATE_WEEKDAY_PHASE) == FIRST_DAY_COL + 3


class TestOutgoingSameDayCheckoutCodes:
    def test_skips_outgoing_when_checkout_equals_next_checkin(self) -> None:
        bookings = [
            _booking(T2, "2026-06-01", "2026-06-05", confirmation_code="OUT"),
            _booking(T2, "2026-06-05", "2026-06-10", confirmation_code="IN"),
        ]
        assert outgoing_same_day_checkout_codes(bookings) == {"OUT"}
