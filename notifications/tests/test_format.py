"""Tests for booking push notification message formatting."""

from __future__ import annotations

from datetime import date

from notifications.format import format_afternoon_notification, format_morning_notification

T0 = "Estúdio Renovado c/ metro à porta"
T1 = "T1 Renovado c/ metro à porta"
EA = "Espaço Renovado a 5 minutos a pé da Ponte Luíz I"
EB = "Loft c/ Varanda Solarenga a 5 Minutos Ponte Luíz I"


def _entry(
    listing_name: str,
    start_date: str,
    end_date: str,
    *,
    guest_first_name: str | None = None,
) -> dict:
    return {
        "listing": {
            T0: "T0",
            T1: "T1",
            EA: "EA",
            EB: "EB",
        }[listing_name],
        "startDate": start_date,
        "endDate": end_date,
        "guestFirstName": guest_first_name,
    }


def _snapshot(*entries: dict) -> dict:
    return {"bookings": list(entries)}


class TestMorningNotification:
    def test_returns_checkins_for_today_in_label_order(self) -> None:
        snapshot = _snapshot(
            _entry(EA, "2026-07-05", "2026-07-08", guest_first_name="Ana"),
            _entry(T1, "2026-07-05", "2026-07-10", guest_first_name="João"),
            _entry(EB, "2026-07-06", "2026-07-09"),
        )
        result = format_morning_notification(snapshot, on_date=date(2026, 7, 5))
        assert result == {
            "title": "Entradas hoje",
            "body": "T1 — João\nEA — Ana",
            "url": "/airbnb/",
        }

    def test_uses_listing_only_when_guest_name_missing(self) -> None:
        snapshot = _snapshot(_entry(T0, "2026-07-05", "2026-07-07"))
        result = format_morning_notification(snapshot, on_date=date(2026, 7, 5))
        assert result == {"title": "Entradas hoje", "body": "T0", "url": "/airbnb/"}

    def test_returns_none_when_no_checkins_today(self) -> None:
        snapshot = _snapshot(_entry(T1, "2026-07-06", "2026-07-10"))
        assert format_morning_notification(snapshot, on_date=date(2026, 7, 5)) is None


class TestAfternoonNotification:
    def test_returns_tomorrow_checkins_and_checkouts(self) -> None:
        snapshot = _snapshot(
            _entry(T0, "2026-07-04", "2026-07-06"),
            _entry(EB, "2026-07-04", "2026-07-06"),
            _entry(T1, "2026-07-06", "2026-07-10", guest_first_name="João"),
            _entry(EA, "2026-07-06", "2026-07-08", guest_first_name="Ana"),
        )
        result = format_afternoon_notification(snapshot, on_date=date(2026, 7, 5))
        assert result == {
            "title": "Amanhã",
            "body": "Saídas: T0, EB\nEntradas: T1 — João, EA — Ana",
            "url": "/airbnb/",
        }

    def test_returns_only_saidas_when_no_entradas(self) -> None:
        snapshot = _snapshot(
            {
                "listing": "T2",
                "startDate": "2026-07-04",
                "endDate": "2026-07-06",
                "guestFirstName": None,
            }
        )
        result = format_afternoon_notification(snapshot, on_date=date(2026, 7, 5))
        assert result == {"title": "Amanhã", "body": "Saídas: T2", "url": "/airbnb/"}

    def test_returns_only_entradas_when_no_saidas(self) -> None:
        snapshot = _snapshot(_entry(T1, "2026-07-06", "2026-07-09", guest_first_name="Maria"))
        result = format_afternoon_notification(snapshot, on_date=date(2026, 7, 5))
        assert result == {
            "title": "Amanhã",
            "body": "Entradas: T1 — Maria",
            "url": "/airbnb/",
        }

    def test_returns_none_when_tomorrow_is_empty(self) -> None:
        snapshot = _snapshot(_entry(T1, "2026-07-08", "2026-07-12"))
        assert format_afternoon_notification(snapshot, on_date=date(2026, 7, 5)) is None
