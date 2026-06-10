"""Calendar grid model for HTML export (mirrors cleanings/main.py stay rules)."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

from cleanings.main import (
    FIRST_DAY_COL,
    LAST_DAY_COL,
    TEMPLATE_WEEKDAY_PHASE,
    booking_listing_label,
    is_weekend_column,
    outgoing_same_day_checkout_codes,
    start_column_for_month,
    stay_guest_label,
)

LISTING_ROW_ORDER = ("T2", "T1", "T0", "EA", "EB")

LISTING_COLORS: dict[str, str] = {
    "T2": "#92D050",
    "T1": "#FABF8F",
    "T0": "#B8CCE4",
    "EA": "#C00000",
    "EB": "#B2A1C7",
}

WEEKEND_COLOR = "#EBEDF0"

WEEKDAY_HEADERS = ("S", "T", "Q", "Q", "S", "S", "D")


@dataclass(frozen=True)
class OccupiedCell:
    listing: str
    day: date
    guest_label: str
    confirmation_code: str | None
    start_date: date
    end_date: date


@dataclass(frozen=True)
class GridColumn:
    """One column slot in the month grid (aligned to the Excel template)."""

    column_index: int
    day: int | None
    is_weekend: bool
    weekday_label: str


def build_occupied_cells(
    year: int, bookings: list[dict]
) -> dict[date, dict[str, OccupiedCell]]:
    """Map each occupied calendar day to listing -> cell metadata."""
    occupied: dict[date, dict[str, OccupiedCell]] = {}
    skipped_outgoing_codes = outgoing_same_day_checkout_codes(bookings)

    for booking in bookings:
        label = booking_listing_label(booking)
        if not label:
            continue

        start = date.fromisoformat(booking["startDate"])
        end = date.fromisoformat(booking["endDate"])
        guest_label = stay_guest_label(booking)
        confirmation_code = booking.get("confirmationCode")
        current = start

        while current <= end:
            if (
                confirmation_code in skipped_outgoing_codes
                and current == end
            ):
                current += timedelta(days=1)
                continue
            if current.year == year:
                show_guest = guest_label if current == start else ""
                occupied.setdefault(current, {})[label] = OccupiedCell(
                    listing=label,
                    day=current,
                    guest_label=show_guest,
                    confirmation_code=confirmation_code,
                    start_date=start,
                    end_date=end,
                )
            current += timedelta(days=1)

    return occupied


def month_grid(
    year: int,
    month: int,
    *,
    phase: int = TEMPLATE_WEEKDAY_PHASE,
) -> list[GridColumn]:
    """Build column slots for a month (day numbers + weekend flags)."""
    num_days = calendar.monthrange(year, month)[1]
    start_col = start_column_for_month(year, month, phase)
    end_col = start_col + num_days - 1
    if end_col > LAST_DAY_COL:
        raise ValueError(
            f"Month {month}/{year} exceeds template grid width "
            f"(ends at column {end_col}, max {LAST_DAY_COL})"
        )

    columns: list[GridColumn] = []
    for col in range(FIRST_DAY_COL, LAST_DAY_COL + 1):
        slot = col - FIRST_DAY_COL
        weekday_label = WEEKDAY_HEADERS[(slot + phase) % 7]
        if start_col <= col <= end_col:
            day_num = col - start_col + 1
        else:
            day_num = None
        columns.append(
            GridColumn(
                column_index=col,
                day=day_num,
                is_weekend=is_weekend_column(col, phase),
                weekday_label=weekday_label,
            )
        )
    return columns
