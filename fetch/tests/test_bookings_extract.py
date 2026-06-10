from datetime import date

import pytest

from fetch.bookings_extract import _date_range, parse_start_month


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
