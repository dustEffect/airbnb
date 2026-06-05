"""Format bookings.json as a checkout calendar text file."""

from __future__ import annotations

import difflib
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

BOOKINGS_FILENAME = "bookings.json"
CHECKOUTS_FILENAME = "bookings.txt"
WARNING_ICON = "⚠️"
GAP_DAYS_FOR_DAY_MARKER = 3
GAP_DAYS_FOR_QUESTION_MARKER = 7

LISTING_LABELS: dict[str, str] = {
    "Totalmente Renovado, metro à porta": "T2",
    "Estúdio Renovado c/ metro à porta": "T0",
    "T1 Renovado c/ metro à porta": "T1",
    "Espaço Renovado a 5 minutos a pé da Ponte Luíz I": "EA",
    "Loft c/ Varanda Solarenga a 5 Minutos Ponte Luíz I": "EB",
}

LABEL_ORDER = ["T0", "T1", "T2", "EA", "EB"]

MONTH_NAMES_PT = (
    "JAN.",
    "FEV.",
    "MAR.",
    "ABR.",
    "MAI.",
    "JUN.",
    "JUL.",
    "AGO.",
    "SET.",
    "OUT.",
    "NOV.",
    "DEZ.",
)

WEEKDAY_NAMES_PT = ("seg.", "ter.", "qua.", "qui.", "sex.", "sáb.", "dom.")


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def bookings_input_path(root: Path | None = None) -> Path:
    return (root or project_root()) / BOOKINGS_FILENAME


def checkouts_output_path(root: Path | None = None) -> Path:
    return (root or project_root()) / CHECKOUTS_FILENAME


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _listing_label(listing_name: str | None) -> str | None:
    if not listing_name:
        return None
    return LISTING_LABELS.get(listing_name.strip())


def _next_checkin_for_listing(
    bookings: list[dict],
    listing_name: str,
    after_date: date,
) -> dict | None:
    candidates = [
        booking
        for booking in bookings
        if booking.get("listingName") == listing_name
        and _parse_date(booking["startDate"]) > after_date
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda booking: booking["startDate"])


def _format_checkout_line(
    checkout_date: date,
    label: str,
    bookings: list[dict],
    listing_name: str,
) -> str:
    parts = [f"{checkout_date.day} {WEEKDAY_NAMES_PT[checkout_date.weekday()]}"]

    next_checkin = _next_checkin_for_listing(bookings, listing_name, checkout_date)
    day_after = checkout_date + timedelta(days=1)
    same_listing_turnover = bool(
        next_checkin and _parse_date(next_checkin["startDate"]) == day_after
    )

    if next_checkin:
        next_date = _parse_date(next_checkin["startDate"])
        gap_days = (next_date - checkout_date).days
        if gap_days >= GAP_DAYS_FOR_QUESTION_MARKER:
            parts.append("a ?")
        elif gap_days > GAP_DAYS_FOR_DAY_MARKER:
            parts.append(f"a {next_date.day}")

    parts.append(label)

    if same_listing_turnover:
        parts.append(WARNING_ICON)

    return " ".join(parts)


def format_checkouts_text(bookings_payload: dict) -> str:
    bookings = bookings_payload.get("bookings", [])
    checkouts: list[tuple[date, str, str]] = []

    for booking in bookings:
        listing_name = booking.get("listingName")
        label = _listing_label(listing_name)
        end_date = booking.get("endDate")
        if not label or not end_date:
            continue
        checkouts.append((_parse_date(end_date), label, listing_name))

    checkouts.sort(key=lambda item: (item[0], LABEL_ORDER.index(item[1])))

    lines: list[str] = []
    current_month: tuple[int, int] | None = None

    for checkout_date, label, listing_name in checkouts:
        month_key = (checkout_date.year, checkout_date.month)
        if month_key != current_month:
            current_month = month_key
            lines.append(MONTH_NAMES_PT[checkout_date.month - 1])
        lines.append(
            _format_checkout_line(checkout_date, label, bookings, listing_name)
        )

    return "\n".join(lines) + ("\n" if lines else "")


def write_checkouts_text(
    bookings_path: Path | None = None,
    *,
    root: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    """Read bookings.json and write bookings.txt checkout summary."""
    in_path = bookings_path or bookings_input_path(root)
    out_path = output_path or checkouts_output_path(root)

    payload = json.loads(in_path.read_text(encoding="utf-8"))
    text = format_checkouts_text(payload)
    out_path.write_text(text, encoding="utf-8")
    if text:
        print(text, end="" if text.endswith("\n") else "\n", flush=True)
    line_count = len([line for line in text.splitlines() if line and not line.endswith(".")])
    print(
        f"Wrote checkout summary to {out_path} ({line_count} checkouts).",
        flush=True,
        file=sys.stderr,
    )
    return out_path


def print_checkouts_diff(
    new_text: str,
    *,
    root: Path | None = None,
    existing_path: Path | None = None,
) -> bool:
    """
    Print checkout row differences between existing bookings.txt and new_text.
    Returns True when any difference was printed.
    """
    path = existing_path or checkouts_output_path(root)
    new_lines = new_text.splitlines()
    old_lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []

    if old_lines == new_lines:
        return False

    for line in difflib.ndiff(old_lines, new_lines):
        if line.startswith("- "):
            print(f"- {line[2:]}")
        elif line.startswith("+ "):
            print(f"+ {line[2:]}")

    return True


def print_checkouts_diff_from_payload(
    bookings_payload: dict,
    *,
    root: Path | None = None,
    existing_path: Path | None = None,
) -> bool:
    """Format payload and print checkout row differences to stdout."""
    return print_checkouts_diff(
        format_checkouts_text(bookings_payload),
        root=root,
        existing_path=existing_path,
    )
