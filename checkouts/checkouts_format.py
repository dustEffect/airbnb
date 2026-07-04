"""Format bookings.json as a checkout calendar text file."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from shared.listing_labels import LABEL_ORDER, LISTING_LABELS
from shared.paths import (
    CHECKOUTS_DIR,
    CHECKOUTS_SUMMARY_FILENAME,
    bookings_json_path,
    checkouts_summary_path,
)

DIFF_SECTION_HEADER = "=== Changes (from tomorrow) ==="
SUMMARY_SECTION_HEADER = f"=== {CHECKOUTS_DIR}/{CHECKOUTS_SUMMARY_FILENAME} ==="
WARNING_ICON = "⚠️"
GAP_DAYS_FOR_DAY_MARKER = 3
GAP_DAYS_FOR_QUESTION_MARKER = 7

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

_MONTH_HEADERS = frozenset(MONTH_NAMES_PT)
_MONTH_ORDER = {header[:-1]: index for index, header in enumerate(MONTH_NAMES_PT)}
_PARENTHETICAL_RE = re.compile(r"\s*\([^)]*\)")

WEEKDAY_NAMES_PT = ("seg.", "ter.", "qua.", "qui.", "sex.", "sáb.", "dom.")


def bookings_input_path(root: Path | None = None) -> Path:
    return bookings_json_path(root)


def checkouts_output_path(root: Path | None = None) -> Path:
    return checkouts_summary_path(root)


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


def format_checkouts_text(
    bookings_payload: dict,
    *,
    min_checkout_date: date | None = None,
) -> str:
    bookings = bookings_payload.get("bookings", [])
    checkouts: list[tuple[date, str, str]] = []

    for booking in bookings:
        listing_name = booking.get("listingName")
        label = _listing_label(listing_name)
        end_date = booking.get("endDate")
        if not label or not end_date:
            continue
        checkout_date = _parse_date(end_date)
        if min_checkout_date is not None and checkout_date < min_checkout_date:
            continue
        checkouts.append((checkout_date, label, listing_name))

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


def format_upcoming_checkouts_text(
    bookings_payload: dict,
    *,
    from_date: date | None = None,
) -> str:
    """Checkout summary for Saídas: full rows from tomorrow onward."""
    min_date = from_date if from_date is not None else _default_diff_from_date()
    return format_checkouts_text(bookings_payload, min_checkout_date=min_date)


def _print_stdout_section(header: str) -> None:
    print(flush=True)
    print(header, flush=True)
    print(flush=True)


def write_checkouts_text(
    bookings_path: Path | None = None,
    *,
    root: Path | None = None,
    output_path: Path | None = None,
    print_to_stdout: bool = True,
    section_header: str | None = None,
) -> Path:
    """Read shared/bookings.json and write checkouts/checkouts.txt checkout summary."""
    in_path = bookings_path or bookings_input_path(root)
    out_path = output_path or checkouts_output_path(root)

    payload = json.loads(in_path.read_text(encoding="utf-8"))
    text = format_checkouts_text(payload)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    if print_to_stdout and text:
        if section_header is not None:
            _print_stdout_section(section_header)
        print(text, end="" if text.endswith("\n") else "\n", flush=True)
    return out_path


def _month_label(header: str) -> str:
    return header[:-1] if header in _MONTH_HEADERS else ""


def _parse_checkout_row(line: str) -> str | None:
    """
    Return the base key "LABEL DAY WEEKDAY" (e.g. "EB 8 seg.") for a checkout row.
    Each listing unit (T0, T1, T2, EA, EB) is bucketed independently so diffs
    are always within the same unit — never across different units.
    Returns None for month headers and unparseable rows.
    """
    if line in _MONTH_HEADERS:
        return None
    cleaned = _PARENTHETICAL_RE.sub("", line.replace(WARNING_ICON, "")).strip()
    parts = cleaned.split()
    if len(parts) < 3:
        return None
    label = parts[-1]
    return f"{label} {parts[0]} {parts[1]}"


def _match_rows(
    old_lines: list[str],
    new_lines: list[str],
) -> tuple[list[str], list[str]]:
    """
    Match old and new checkout lines for the same listing unit on the same day.

    All lines in the same group share label + checkout day + weekday; only the
    gap window and warning icon vary, and both are ignored.  Matching is therefore
    purely by count: any old line pairs with any new line.
    Returns (unmatched_old_lines, unmatched_new_lines).
    """
    n_matched = min(len(old_lines), len(new_lines))
    return old_lines[n_matched:], new_lines[n_matched:]


def _checkouts_by_month(
    lines: list[str],
) -> dict[str, dict[str, list[str]]]:
    """
    Group checkout lines by month, then by base key ("LABEL DAY WEEKDAY").
    Each listing unit on each day gets its own bucket; diffs never cross units.
    """
    by_month: dict[str, dict[str, list[str]]] = {}
    current_month = ""

    for line in lines:
        month = _month_label(line)
        if month:
            current_month = month
            continue

        base_key = _parse_checkout_row(line)
        if not base_key:
            continue

        if current_month not in by_month:
            by_month[current_month] = defaultdict(list)
        by_month[current_month][base_key].append(line)

    return by_month


def _sort_checkout_key(key: str) -> tuple[int, int, str]:
    # key is "LABEL DAY WEEKDAY" (e.g. "EB 8 seg.")
    parts = key.split()
    label = parts[0]
    day = int(parts[1])
    label_index = LABEL_ORDER.index(label) if label in LABEL_ORDER else len(LABEL_ORDER)
    return (day, label_index, key)


def _checkout_date_from_diff_key(month: str, key: str, *, year: int) -> date | None:
    month_index = _MONTH_ORDER.get(month)
    if month_index is None:
        return None
    try:
        day = int(key.split()[1])  # key is "LABEL DAY WEEKDAY"
        return date(year, month_index + 1, day)
    except (ValueError, IndexError):
        return None


def _default_diff_from_date() -> date:
    return date.today() + timedelta(days=1)


def print_checkouts_diff(
    new_text: str,
    *,
    root: Path | None = None,
    existing_path: Path | None = None,
    diff_from_date: date | None = None,
    reference_year: int | None = None,
    section_header: str | None = None,
) -> bool:
    """
    Print checkout row differences between existing checkouts.txt and new_text.

    Each listing unit (T0, T1, T2, EA, EB) is diffed independently against its
    own past data — comparisons never cross unit boundaries.  Within each unit,
    any gap window (a ?, a N, or absent) and warning icons are ignored.
    Warning icons and parenthetical times are ignored.

    By default only checkouts on or after tomorrow are included.
    Each month's changes are prefixed with a short month label (e.g. JUN, AGO).
    Returns True when any difference was printed.
    """
    path = existing_path or checkouts_output_path(root)
    new_lines = new_text.splitlines()
    old_lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []

    diff_from = diff_from_date if diff_from_date is not None else _default_diff_from_date()
    year = reference_year if reference_year is not None else date.today().year

    old_by_month = _checkouts_by_month(old_lines)
    new_by_month = _checkouts_by_month(new_lines)
    all_months = sorted(
        set(old_by_month) | set(new_by_month),
        key=lambda month: _MONTH_ORDER.get(month, len(MONTH_NAMES_PT)),
    )

    if section_header is not None:
        _print_stdout_section(section_header)

    printed_any = False
    for month in all_months:
        old_groups = old_by_month.get(month, {})
        new_groups = new_by_month.get(month, {})
        all_base_keys = sorted(
            set(old_groups) | set(new_groups),
            key=_sort_checkout_key,
        )

        removals: list[str] = []
        additions: list[str] = []
        for base_key in all_base_keys:
            checkout_date = _checkout_date_from_diff_key(month, base_key, year=year)
            if checkout_date is None or checkout_date < diff_from:
                continue

            old_rows = old_groups.get(base_key, [])
            new_rows = new_groups.get(base_key, [])
            unmatched_old, unmatched_new = _match_rows(old_rows, new_rows)
            for line in unmatched_old:
                removals.append(f"(caiu) {line}")
            for line in unmatched_new:
                additions.append(f"+ {line}")

        month_output = removals + additions
        if month_output:
            print(month)
            for line in month_output:
                print(line)
            printed_any = True

    if section_header is not None and not printed_any:
        print("(no changes)", flush=True)

    return printed_any


def print_checkouts_diff_from_payload(
    bookings_payload: dict,
    *,
    root: Path | None = None,
    existing_path: Path | None = None,
    diff_from_date: date | None = None,
    section_header: str | None = None,
) -> bool:
    """Format payload and print checkout row differences to stdout."""
    date_range = bookings_payload.get("dateRange") or {}
    start_date = date_range.get("startDate", "")
    reference_year = int(start_date[:4]) if len(start_date) >= 4 else date.today().year
    return print_checkouts_diff(
        format_checkouts_text(bookings_payload),
        root=root,
        existing_path=existing_path,
        diff_from_date=diff_from_date,
        reference_year=reference_year,
        section_header=section_header,
    )
