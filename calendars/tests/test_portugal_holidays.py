"""Tests for calendars/portugal_holidays.py."""

from __future__ import annotations

from datetime import date

from calendars.portugal_holidays import portugal_national_holidays


class TestPortugalNationalHolidays:
    def test_includes_fixed_and_movable_holidays_for_2026(self) -> None:
        holidays = portugal_national_holidays(2026)
        assert holidays[date(2026, 1, 1)] == "Ano Novo"
        assert holidays[date(2026, 4, 25)] == "Dia da Liberdade"
        assert holidays[date(2026, 12, 25)] == "Natal"
        assert holidays[date(2026, 4, 3)] == "Sexta-feira Santa"
        assert holidays[date(2026, 6, 4)] == "Corpo de Deus"
        assert len(holidays) == 12
