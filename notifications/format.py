"""Format booking snapshot data as push notification messages."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from shared.listing_labels import LABEL_ORDER

NOTIFICATION_URL = "/airbnb/"


def format_test_notification(*, now: datetime) -> dict[str, str]:
    """Fixed test message; always sent (never skipped)."""
    stamp = now.strftime("%Y-%m-%d %H:%M")
    return {
        "title": "Teste",
        "body": f"Notificação de teste — {stamp} (Lisboa)",
        "url": NOTIFICATION_URL,
    }


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _format_checkin_entry(label: str, guest_first_name: str | None) -> str:
    first = (guest_first_name or "").strip()
    return f"{label} — {first}" if first else label


def _sort_labels(labels: list[str]) -> list[str]:
    order = {label: index for index, label in enumerate(LABEL_ORDER)}
    return sorted(labels, key=lambda label: order.get(label, len(LABEL_ORDER)))


def _checkins_on(snapshot: dict, day: date) -> list[dict]:
    day_text = day.isoformat()
    matches = [
        booking
        for booking in snapshot.get("bookings", [])
        if booking.get("startDate") == day_text and booking.get("listing")
    ]
    matches.sort(
        key=lambda booking: LABEL_ORDER.index(booking["listing"])
        if booking["listing"] in LABEL_ORDER
        else len(LABEL_ORDER)
    )
    return matches


def _checkouts_on(snapshot: dict, day: date) -> list[str]:
    day_text = day.isoformat()
    labels = [
        booking["listing"]
        for booking in snapshot.get("bookings", [])
        if booking.get("endDate") == day_text and booking.get("listing")
    ]
    return _sort_labels(labels)


def format_morning_notification(
    snapshot: dict,
    *,
    on_date: date,
) -> dict[str, str] | None:
    """Today's check-ins. Returns {title, body, url} or None when empty."""
    checkins = _checkins_on(snapshot, on_date)
    if not checkins:
        return None
    lines = [
        _format_checkin_entry(booking["listing"], booking.get("guestFirstName"))
        for booking in checkins
    ]
    return {
        "title": "Entradas hoje",
        "body": "\n".join(lines),
        "url": NOTIFICATION_URL,
    }


def format_afternoon_notification(
    snapshot: dict,
    *,
    on_date: date,
) -> dict[str, str] | None:
    """Tomorrow's check-ins and check-outs. Returns {title, body, url} or None."""
    tomorrow = on_date + timedelta(days=1)
    sections: list[str] = []

    checkout_labels = _checkouts_on(snapshot, tomorrow)
    if checkout_labels:
        sections.append(f"Saídas: {', '.join(checkout_labels)}")

    checkins = _checkins_on(snapshot, tomorrow)
    if checkins:
        entries = [
            _format_checkin_entry(booking["listing"], booking.get("guestFirstName"))
            for booking in checkins
        ]
        sections.append(f"Entradas: {', '.join(entries)}")

    if not sections:
        return None
    return {
        "title": "Amanhã",
        "body": "\n".join(sections),
        "url": NOTIFICATION_URL,
    }
