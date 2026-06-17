from datetime import date

import pytest

from fetch.bookings_extract import (
    ACCEPTED_BOOKING_STATUS,
    _date_range,
    _reservations_from_payload,
    is_accepted_booking_status,
    parse_start_month,
)


class TestParseStartMonth:
    def test_parses_year_month(self) -> None:
        assert parse_start_month("2026-06") == date(2026, 6, 1)

    def test_rejects_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="YYYY-MM"):
            parse_start_month("06-2026")


class TestDateRange:
    def test_defaults_to_today(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class FixedDate(date):
            @classmethod
            def today(cls) -> date:
                return cls(2026, 6, 5)

        monkeypatch.setattr("fetch.bookings_extract.date", FixedDate)
        start, end = _date_range(2)
        assert start == "2026-06-05"
        assert end == "2026-08-06"

    def test_uses_from_month_as_start(self) -> None:
        start, end = _date_range(2, from_month=date(2026, 8, 1))
        assert start == "2026-08-01"
        assert end == "2026-10-02"

    def test_calendar_year_covers_full_year(self) -> None:
        start, end = _date_range(calendar_year=2026)
        assert start == "2026-01-01"
        assert end == "2026-12-31"


class TestReservationsFromPayload:
    def _payload_with_reservation(self, *, code: str, status: str) -> dict:
        return {
            "data": {
                "patek": {
                    "getMultiCalendarListingsAndCalendars": {
                        "hostCalendarsResponse": {
                            "calendars": [
                                {
                                    "listingId": "123",
                                    "listingAttributes": {
                                        "listingName": "T1 Renovado c/ metro à porta"
                                    },
                                    "days": [
                                        {
                                            "unavailabilityReasons": {
                                                "reservation": {
                                                    "confirmationCode": code,
                                                    "statusString": status,
                                                    "hostingId": "123",
                                                    "startDate": "2026-06-10",
                                                    "endDate": "2026-06-12",
                                                    "numberOfAdults": 2,
                                                }
                                            }
                                        }
                                    ],
                                }
                            ]
                        }
                    }
                }
            }
        }

    def test_keeps_accepted_reservations(self) -> None:
        reservations = _reservations_from_payload(
            self._payload_with_reservation(code="HMACEPTED", status=ACCEPTED_BOOKING_STATUS),
            {},
        )
        assert list(reservations) == ["HMACEPTED"]
        assert reservations["HMACEPTED"]["status"] == ACCEPTED_BOOKING_STATUS

    def test_skips_pending_reservations(self) -> None:
        reservations = _reservations_from_payload(
            self._payload_with_reservation(code="HMPENDING", status="Pendente"),
            {},
        )
        assert reservations == {}

    def test_is_accepted_booking_status(self) -> None:
        assert is_accepted_booking_status(ACCEPTED_BOOKING_STATUS) is True
        assert is_accepted_booking_status("Pendente") is False
        assert is_accepted_booking_status(None) is False
