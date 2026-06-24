"""Booking and calendar-grid helpers for the stay calendar HTML export."""

from __future__ import annotations

from datetime import date, timedelta

from shared.listing_labels import LISTING_LABELS

FIRST_DAY_COL = 4  # D
LAST_DAY_COL = 40  # AN — one past AM so long months fit the weekday row
TEMPLATE_WEEKDAY_PHASE = 0  # column D = Monday

MONTHS_PT = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


def year_from_bookings(data: dict) -> int:
    return int(data["dateRange"]["startDate"][:4])


def booking_listing_label(booking: dict) -> str | None:
    listing_name = booking.get("listingName")
    if not listing_name:
        return None
    return LISTING_LABELS.get(listing_name.strip())


def stay_guest_label(booking: dict) -> str:
    parts: list[str] = []
    adults = booking.get("numberOfAdults", 0)
    children = booking.get("numberOfChildren", 0)
    infants = booking.get("numberOfInfants", 0)
    if adults:
        parts.append(f"{adults}a")
    if children:
        parts.append(f"{children}c")
    if infants:
        parts.append(f"{infants}b")
    return " ".join(parts)


def outgoing_same_day_checkout_codes(bookings: list[dict]) -> set[str]:
    """Confirmation codes for outgoing stays that share checkout/check-in day."""
    skipped_codes: set[str] = set()
    by_label: dict[str, list[dict]] = {}

    for booking in bookings:
        label = booking_listing_label(booking)
        if not label:
            continue
        by_label.setdefault(label, []).append(booking)

    for listing_bookings in by_label.values():
        listing_bookings.sort(key=lambda booking: booking["startDate"])
        for index in range(len(listing_bookings) - 1):
            checkout = date.fromisoformat(listing_bookings[index]["endDate"])
            checkin = date.fromisoformat(listing_bookings[index + 1]["startDate"])
            if checkout == checkin:
                code = listing_bookings[index].get("confirmationCode")
                if code:
                    skipped_codes.add(code)

    return skipped_codes


def start_column_for_month(year: int, month: int, phase: int) -> int:
    first_weekday = date(year, month, 1).weekday()
    for col in range(FIRST_DAY_COL, LAST_DAY_COL + 1):
        if (col - FIRST_DAY_COL + phase) % 7 == first_weekday:
            return col
    raise ValueError(f"No weekday column found for {year}-{month:02d}")


def is_weekend_column(col: int, phase: int) -> bool:
    return (col - FIRST_DAY_COL + phase) % 7 in (5, 6)
