"""Render the stay calendar as a self-contained HTML file."""

from __future__ import annotations

import html
import json
from datetime import date, timedelta
from pathlib import Path

from calendars.calendar_model import (
    LISTING_COLORS,
    LISTING_ROW_ORDER,
    WEEKEND_COLOR,
    GridColumn,
    OccupiedCell,
    build_occupied_cells,
    month_grid,
)
from calendars.booking_helpers import MONTHS_PT
from calendars.portugal_holidays import portugal_national_holidays
from checkouts.checkouts_format import format_upcoming_checkouts_text
from shared.pwa import pwa_icon_url, pwa_manifest_url, pwa_sw_url, PWA_SPLASH_BACKGROUND, vapid_public_key

HOLIDAY_ICON = "🇵🇹"
HOLIDAY_BG = "#D4A017"
HOLIDAY_BORDER = "#A67C00"
CUSTOM_STAY_COLOR = "#B2A1C7"
AIRBNB_STAY_URL = "https://www.airbnb.pt/hosting/stay/"
SAIDAS_EMPTY_MESSAGE = "Sem saídas agendadas."

_ICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"'
    ' fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"'
    ' stroke-linejoin="round" aria-hidden="true">{paths}</svg>'
)
_ICON_BED = _ICON.format(
    paths=(
        '<path d="M2 4v16"/><path d="M2 8h20a2 2 0 0 1 2 2v10"/>'
        '<path d="M2 17h20"/><path d="M6 8v9"/>'
    )
)
_ICON_TRASH = _ICON.format(
    paths=(
        '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>'
        '<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
    )
)
_ICON_X = _ICON.format(paths='<path d="M18 6 6 18"/><path d="m6 6 12 12"/>')
_ICON_CHECK = _ICON.format(paths='<path d="M20 6 9 17l-5-5"/>')
_ICON_PLUS = _ICON.format(paths='<path d="M12 5v14"/><path d="M5 12h14"/>')
_ICON_TODAY = _ICON.format(
    paths=(
        '<path d="M8 2v4"/>'
        '<path d="M16 2v4"/>'
        '<rect width="18" height="18" x="3" y="4" rx="2"/>'
        '<path d="M3 10h18"/>'
        '<circle cx="12" cy="16" r="2.75" stroke="#dc2626"/>'
    )
)

_CSS = """
:root {
  --bg: #f4f5f7;
  --card: #ffffff;
  --text: #1a1a1a;
  --muted: #6b7280;
  --border: #d1d5db;
  --nav-bg: #ffffff;
  --nav-shadow: 0 1px 3px rgba(0,0,0,.08);
  --day-size: 2rem;
  --listing-size: 2.25rem;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.4;
}
header {
  background: var(--card);
  border-bottom: 1px solid var(--border);
  padding: 1rem 1.25rem 1.25rem;
}
header h1 { margin: 0; font-size: 1.5rem; font-weight: 600; }
.page-title-btn {
  all: unset;
  display: block;
  width: 100%;
  font: inherit;
  font-size: inherit;
  font-weight: inherit;
  line-height: inherit;
  color: inherit;
  text-align: inherit;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
}
nav.month-nav {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  flex-wrap: wrap;
  gap: .35rem;
  padding: .6rem 1rem;
  background: var(--nav-bg);
  box-shadow: var(--nav-shadow);
  border-bottom: 1px solid var(--border);
  -webkit-overflow-scrolling: touch;
}
nav.month-nav a {
  color: #2563eb;
  text-decoration: none;
  font-size: .8rem;
  padding: .2rem .45rem;
  border-radius: 4px;
  flex: 0 0 auto;
}
nav.month-nav a:hover { background: #eff6ff; }
main {
  padding: 1rem;
  max-width: 1400px;
  margin: 0 auto;
  padding-left: max(1rem, env(safe-area-inset-left));
  padding-right: max(1rem, env(safe-area-inset-right));
}
.month-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 1.25rem;
  overflow: hidden;
  scroll-margin-top: 3.5rem;
}
.month-card h2 {
  margin: 0;
  padding: .75rem 1rem;
  font-size: 1.1rem;
  background: #f9fafb;
  border-bottom: 1px solid var(--border);
}
.month-scroll {
  overflow-x: auto;
  padding: .75rem 1rem 1rem;
  -webkit-overflow-scrolling: touch;
  scroll-padding-left: 2.6rem;
}
.grid {
  position: relative;
  display: grid;
  gap: 2px;
  width: max-content;
  min-width: 100%;
}
.cell {
  width: var(--day-size);
  min-width: var(--day-size);
  height: var(--day-size);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: .7rem;
  border: 1px solid var(--border);
  border-radius: 3px;
  background: #fff;
}
.cell.header {
  background: #f3f4f6;
  font-weight: 600;
  color: var(--muted);
  font-size: .65rem;
}
.cell.weekday-header {
  cursor: pointer;
  user-select: none;
}
.cell.weekday-header.has-icon {
  font-size: .85rem;
  line-height: 1;
}
.cell.weekday-header.has-holiday {
  background: var(--holiday-bg, #d4a017);
  border-color: var(--holiday-border, #a67c00);
}
.cell.weekday-header .weekday-letter {
  font-size: .65rem;
}
.cell.weekday-header .holiday-marker {
  font-size: .85rem;
  line-height: 1;
}
.cell.day-num {
  font-weight: 600;
  font-size: .75rem;
}
.cell.day-num.is-today::before {
  content: "";
  position: absolute;
  width: calc(100% - 4px);
  height: calc(100% - 4px);
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  border: 2px solid #dc2626;
  border-radius: 50%;
  pointer-events: none;
}
.cell.weekend-empty { background: var(--weekend-bg, #ebedf0); }
.cell.listing-label {
  width: 2.5rem;
  min-width: 2.5rem;
  font-weight: 700;
  font-size: .75rem;
  background: rgba(249, 250, 251, 0.8);
  border-color: transparent;
  justify-content: center;
  padding: 0;
  position: sticky;
  left: 0;
  z-index: 2;
  box-shadow: 2px 0 4px rgba(0, 0, 0, 0.05);
}
.cell.listing-label.listing-label-row {
  height: var(--listing-size);
}
.cell.listing-row {
  height: var(--listing-size);
  font-weight: 600;
  font-size: .65rem;
  padding: 0 .15rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cell.stay {
  color: #111;
  border-color: rgba(0,0,0,.15);
  background: var(--stay-color);
  opacity: 0.8;
}
.cell.stay.stay-end,
.cell.stay-custom.stay-end {
  --empty-bg: #fff;
  border-right-color: var(--border);
  background: linear-gradient(
    to right,
    var(--stay-color) 0%,
    var(--stay-color) 50%,
    var(--empty-bg) 100%
  ) !important;
}
.cell.stay.stay-end.weekend-end,
.cell.stay-custom.stay-end.weekend-end {
  --empty-bg: var(--weekend-bg, #ebedf0);
}
.cell.stay-comment,
.cell.day-comment {
  cursor: pointer;
  position: relative;
  touch-action: manipulation;
}
.cell.stay-comment:hover,
.cell.day-comment:hover { outline: 2px solid #2563eb; outline-offset: -2px; }
.cell.stay-comment:focus-visible,
.cell.day-comment:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: -2px;
}
.cell.stay-comment.has-comment,
.cell.day-comment.has-comment {
  border: 2px dashed #1d4ed8 !important;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.65);
}
.cell.stay-comment.has-comment::after,
.cell.day-comment.has-comment::after {
  content: "";
  position: absolute;
  top: 2px;
  right: 2px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #1d4ed8;
  box-shadow: 0 0 0 1px #fff;
  pointer-events: none;
}
.comment-backdrop {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.35);
  z-index: 100;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}
.comment-backdrop.open { display: flex; }
.comment-dialog {
  background: var(--card);
  border-radius: 10px;
  padding: 1.25rem;
  width: min(24rem, 100%);
  min-width: min(100%, 13.5rem);
  box-shadow: 0 8px 30px rgba(0,0,0,.18);
}
.comment-dialog-header {
  display: flex;
  align-items: baseline;
  gap: .5rem;
  flex-wrap: wrap;
  margin-bottom: .75rem;
}
.comment-dialog-header h3 {
  margin: 0;
  font-size: 1rem;
}
.comment-dialog-header .meta {
  margin: 0;
  font-size: .8rem;
  color: var(--muted);
}
.comment-dialog textarea {
  width: 100%;
  min-height: 5rem;
  resize: vertical;
  font: inherit;
  padding: .5rem .6rem;
  border: 1px solid var(--border);
  border-radius: 6px;
}
.saidas-dialog {
  width: min(28rem, 100%);
}
.saidas-text {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: .875rem;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: min(60vh, 24rem);
  overflow: auto;
}
.comment-actions {
  display: flex;
  flex-wrap: nowrap;
  gap: .5rem;
  justify-content: flex-end;
  align-items: center;
  margin-top: .75rem;
}
.comment-actions button {
  flex: 0 0 auto;
  font: inherit;
  padding: 0;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: #f9fafb;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 0;
}
.comment-actions button svg { display: block; }
.comment-actions button.primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.comment-actions button.danger { color: #b91c1c; }
.comment-actions button[hidden] { display: none !important; }
.comment-peek {
  position: fixed;
  z-index: 110;
  width: max-content;
  max-width: min(20rem, calc(100vw - 2rem));
  padding: .45rem .6rem;
  background: #fff;
  color: #1a1a1a;
  border: 1px solid #1a1a1a;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,.12);
  pointer-events: none;
  font-size: .85rem;
  line-height: 1.35;
}
.comment-peek p {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
.cell.empty-slot {
  cursor: pointer;
  touch-action: manipulation;
}
.cell.empty-slot.slot-selected {
  outline: 2px solid #2563eb;
  outline-offset: -2px;
  background: #dbeafe !important;
}
.cell.stay-custom {
  --stay-color: #B2A1C7;
  background: var(--stay-color) !important;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.12);
  opacity: 0.8;
}
.stay-label-mask {
  position: absolute;
  pointer-events: none;
  z-index: 3;
  overflow: hidden;
  --grid-gap: 2px;
  -webkit-mask-image: repeating-linear-gradient(
    to right,
    #000 0,
    #000 var(--day-size),
    transparent var(--day-size),
    transparent calc(var(--day-size) + var(--grid-gap))
  );
  mask-image: repeating-linear-gradient(
    to right,
    #000 0,
    #000 var(--day-size),
    transparent var(--day-size),
    transparent calc(var(--day-size) + var(--grid-gap))
  );
}
.stay-label-mask .stay-label {
  position: absolute;
  left: 3px;
  top: 50%;
  transform: translateY(-50%);
  white-space: nowrap;
  line-height: 1.1;
  font-weight: 600;
  font-size: .65rem;
  color: #111;
}
.custom-stay-add {
  position: fixed;
  z-index: 120;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 999px;
  border: 2px solid #1a1a1a;
  background: #fff;
  color: #1a1a1a;
  font-size: 1.6rem;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  touch-action: manipulation;
}
.custom-stay-add:hover { background: #f3f4f6; }
.custom-stay-add[hidden] { display: none !important; }
.scroll-today-btn {
  position: fixed;
  z-index: 110;
  left: max(1rem, env(safe-area-inset-left));
  bottom: max(1rem, env(safe-area-inset-bottom));
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 999px;
  border: 2px solid #1a1a1a;
  background: #fff;
  color: #1a1a1a;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  touch-action: manipulation;
}
.scroll-today-btn:hover { background: #f3f4f6; }
.scroll-today-btn[hidden] { display: none !important; }
.push-subscribe {
  margin-top: 0.75rem;
  font-size: 0.875rem;
}
.push-subscribe-btn {
  all: unset;
  color: #2563eb;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.push-subscribe-btn:disabled {
  color: var(--muted);
  cursor: not-allowed;
  text-decoration: none;
}
.push-subscribe-panel {
  margin-top: 0.5rem;
  padding: 0.75rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  background: var(--bg);
}
.push-subscribe-panel[hidden] { display: none; }
.push-subscribe-panel textarea {
  width: 100%;
  min-height: 6rem;
  margin-top: 0.5rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.75rem;
}
.push-subscribe-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
}
.push-subscribe-actions button {
  border: 1px solid var(--border);
  border-radius: 0.375rem;
  background: var(--card);
  padding: 0.35rem 0.65rem;
  font: inherit;
  font-size: 0.8125rem;
}
.push-subscribe-actions button.primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.push-subscribe-hint {
  margin: 0;
  color: var(--muted);
  font-size: 0.8125rem;
}
#custom-stay-guest {
  width: 100%;
  font: inherit;
  padding: .5rem .6rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-bottom: .75rem;
}
@media (hover: none) {
  .cell.stay-comment:hover,
  .cell.day-comment:hover { outline: none; }
  .cell.stay-comment:active,
  .cell.day-comment:active {
    outline: 2px solid #2563eb;
    outline-offset: -2px;
  }
}
@media (max-width: 768px) {
  nav.month-nav {
    flex-wrap: nowrap;
    overflow-x: auto;
    gap: .45rem;
    padding: .55rem max(.75rem, env(safe-area-inset-left));
    scroll-snap-type: x proximity;
  }
  nav.month-nav a {
    font-size: .85rem;
    padding: .45rem .7rem;
    min-height: 2.25rem;
    display: inline-flex;
    align-items: center;
    background: #f3f4f6;
    scroll-snap-align: start;
  }
  header {
    padding: .85rem max(.85rem, env(safe-area-inset-left))
      1rem max(.85rem, env(safe-area-inset-right));
  }
  header h1 { font-size: 1.2rem; }
  main { padding-top: .65rem; padding-bottom: max(1rem, env(safe-area-inset-bottom)); }
  .month-card { border-radius: 10px; margin-bottom: 1rem; }
  .month-card h2 {
    font-size: 1rem;
    padding: .65rem .85rem;
    position: sticky;
    left: 0;
  }
  .month-scroll {
    padding: .55rem .65rem .85rem;
  }
  .month-scroll::after {
    content: "Deslize para ver mais dias →";
    display: block;
    margin-top: .45rem;
    text-align: center;
    font-size: .72rem;
    color: var(--muted);
  }
  .comment-backdrop.open {
    align-items: flex-end;
    padding: 0;
  }
  .comment-dialog {
    width: 100%;
    max-width: none;
    border-radius: 14px 14px 0 0;
    padding: 1rem 1rem calc(1rem + env(safe-area-inset-bottom));
  }
  .comment-dialog textarea {
    min-height: 6.5rem;
    font-size: 1rem;
  }
  .comment-actions button {
    width: 3rem;
    height: 3rem;
  }
}
@media (max-width: 640px) {
  :root {
    --day-size: 2.15rem;
    --listing-size: 2.35rem;
  }
  .cell {
    font-size: .72rem;
    border-radius: 4px;
  }
  .cell.header { font-size: .68rem; }
  .cell.day-num { font-size: .78rem; }
  .cell.listing-label {
    width: 2.35rem;
    min-width: 2.35rem;
    font-size: .72rem;
  }
  .cell.listing-row {
    font-size: .68rem;
    padding: 0 .2rem;
  }
  .grid { gap: 3px; }
}
"""


def stay_cell_id(listing: str, day: date) -> str:
    """Stable DOM / localStorage key for a stay day cell."""
    return f"{listing}-{day.strftime('%Y%m%d')}"


def day_cell_id(day: date) -> str:
    """Stable DOM / localStorage key for a calendar day-number cell."""
    return f"dia-{day.strftime('%Y%m%d')}"


def _storage_key(year: int) -> str:
    return f"airbnb-cleanings-comments-{year}"


def _weekday_icons_storage_key(year: int) -> str:
    return f"airbnb-cleanings-weekday-icons-{year}"


def _custom_stays_storage_key(year: int) -> str:
    return f"airbnb-custom-stays-{year}"


def weekday_header_id(year: int, month: int, column_index: int) -> str:
    """Stable DOM / localStorage key for a weekday header cell."""
    return f"ac-wh-{year}-{month:02d}-c{column_index:02d}"


def _cell_title(cell: OccupiedCell) -> str:
    parts = [
        f"{cell.listing}: {cell.start_date.isoformat()} → {cell.end_date.isoformat()}",
    ]
    if cell.guest_label:
        parts.append(f"Hóspedes: {cell.guest_label}")
    return " | ".join(parts)


def _stay_identity(stay: OccupiedCell) -> str:
    if stay.confirmation_code:
        return stay.confirmation_code
    return f"{stay.start_date.isoformat()}:{stay.end_date.isoformat()}"


def _is_stay_end_cell(
    stay: OccupiedCell,
    day_date: date,
    occupied: dict[date, dict[str, OccupiedCell]],
    listing: str,
) -> bool:
    """True on the last occupied day of a stay."""
    next_stay = occupied.get(day_date + timedelta(days=1), {}).get(listing)
    if next_stay is None:
        return True
    return _stay_identity(next_stay) != _stay_identity(stay)


def _grid_column(slot_index: int) -> int:
    """Map a month slot index to a CSS grid column (column 1 is the listing label)."""
    return slot_index + 2


def _weekday_header_html(
    col: GridColumn,
    *,
    year: int,
    month: int,
    holidays: dict[date, str],
    grid_col: int,
) -> str:
    label = html.escape(col.weekday_label)
    cls = "cell header weekday-header"
    title_attr = ""

    if col.day is not None:
        day_date = date(year, month, col.day)
        if day_date in holidays:
            cls += " has-holiday"
            holiday_name = html.escape(holidays[day_date], quote=True)
            title_attr = f' title="Feriado: {holiday_name}"'
            content = f'<span class="holiday-marker" aria-hidden="true">{HOLIDAY_ICON}</span>'
        else:
            content = f'<span class="weekday-letter">{label}</span>'
    else:
        content = label

    header_id = weekday_header_id(year, month, col.column_index)
    return (
        f'<div id="{html.escape(header_id)}" class="{cls}"'
        f' style="grid-row:1;grid-column:{grid_col}"'
        f' data-default="{label}"{title_attr}>{content}</div>'
    )


def _render_month(
    year: int,
    month: int,
    month_name: str,
    occupied: dict[date, dict[str, OccupiedCell]],
    holidays: dict[date, str],
) -> str:
    columns = month_grid(year, month)
    num_slots = len(columns)

    grid_style = (
        f"--weekend-bg: {html.escape(WEEKEND_COLOR)};"
        f" --holiday-bg: {HOLIDAY_BG};"
        f" --holiday-border: {HOLIDAY_BORDER};"
        f" grid-template-columns: 2.5rem repeat({num_slots}, var(--day-size));"
    )
    parts: list[str] = [
        f'<section class="month-card" id="{html.escape(month_name.lower())}">',
        f"<h2>{html.escape(month_name)}</h2>",
        '<div class="month-scroll">',
        f'<div class="grid" style="{grid_style}">',
    ]

    for slot_index, col in enumerate(columns):
        grid_col = _grid_column(slot_index)
        parts.append(
            _weekday_header_html(
                col, year=year, month=month, holidays=holidays, grid_col=grid_col
            )
        )

    for slot_index, col in enumerate(columns):
        if col.day is None:
            continue
        grid_col = _grid_column(slot_index)
        cls = "cell day-num day-comment"
        if col.is_weekend:
            cls += " weekend-empty"
        day_date = date(year, month, col.day)
        cell_id = day_cell_id(day_date)
        parts.append(
            f'<div id="{html.escape(cell_id)}"'
            f' class="{cls}"'
            f' style="grid-row:2;grid-column:{grid_col}"'
            f' data-date="{day_date.strftime("%Y%m%d")}"'
            f' role="button" tabindex="0">{col.day}</div>'
        )

    for row_index, listing in enumerate(LISTING_ROW_ORDER, start=3):
        color = LISTING_COLORS[listing]
        parts.append(
            f'<div class="cell listing-label listing-label-row" style="color:{color};'
            f'grid-row:{row_index};grid-column:1">{html.escape(listing)}</div>'
        )
        for slot_index, col in enumerate(columns):
            if col.day is None:
                continue

            grid_col = _grid_column(slot_index)
            day_date = date(year, month, col.day)
            stay = occupied.get(day_date, {}).get(listing)
            if stay:
                title = html.escape(_cell_title(stay), quote=True)
                cell_id = stay_cell_id(listing, day_date)
                stay_key = html.escape(_stay_identity(stay), quote=True)
                stay_classes = ["cell", "listing-row", "stay", "stay-comment"]
                if _is_stay_end_cell(stay, day_date, occupied, listing):
                    stay_classes.append("stay-end")
                    if col.is_weekend:
                        stay_classes.append("weekend-end")
                weekend_attr = ' data-weekend="true"' if col.is_weekend else ""
                guest_label_attr = ""
                if stay.guest_label:
                    guest_label_attr = (
                        f' data-guest-label="{html.escape(stay.guest_label, quote=True)}"'
                    )
                parts.append(
                    f'<div id="{html.escape(cell_id)}"'
                    f' class="{" ".join(stay_classes)}"'
                    f' style="--stay-color:{color};grid-row:{row_index};grid-column:{grid_col}"'
                    f' title="{title}"'
                    f' data-listing="{html.escape(listing)}"'
                    f' data-date="{day_date.strftime("%Y%m%d")}"'
                    f' data-stay-key="{stay_key}"'
                    f'{guest_label_attr}'
                    f'{weekend_attr}'
                    f' role="button" tabindex="0"></div>'
                )
            else:
                cls = "cell listing-row empty-slot"
                if col.is_weekend:
                    cls += " weekend-empty"
                cell_id = stay_cell_id(listing, day_date)
                weekend_attr = ' data-weekend="true"' if col.is_weekend else ""
                parts.append(
                    f'<div id="{html.escape(cell_id)}"'
                    f' class="{cls}"'
                    f' data-listing="{html.escape(listing)}"'
                    f' data-date="{day_date.strftime("%Y%m%d")}"'
                    f'{weekend_attr}'
                    f' style="grid-row:{row_index};grid-column:{grid_col}"></div>'
                )

    parts.extend(["</div>", "</div>", "</section>"])
    return "\n".join(parts)


def _initial_month_section_id(year: int) -> str:
    """Month section id to show first when the page loads."""
    today = date.today()
    if year == today.year:
        month_index = today.month - 1
    elif year < today.year:
        month_index = 11
    else:
        month_index = 0
    return MONTHS_PT[month_index].lower()


def render_calendar_html(
    *,
    year: int,
    bookings: list[dict],
    upcoming_checkouts_text: str | None = None,
) -> str:
    occupied = build_occupied_cells(year, bookings)
    holidays = portugal_national_holidays(year)

    if upcoming_checkouts_text is None:
        upcoming_checkouts_text = format_upcoming_checkouts_text({"bookings": bookings})
    saidas_pre = (
        html.escape(upcoming_checkouts_text.rstrip("\n"))
        if upcoming_checkouts_text.strip()
        else html.escape(SAIDAS_EMPTY_MESSAGE)
    )

    nav_links = "".join(
        f'<a href="#{html.escape(name.lower())}">{html.escape(name)}</a>'
        for name in MONTHS_PT
    )

    months_html = "\n".join(
        _render_month(year, month, name, occupied, holidays)
        for month, name in enumerate(MONTHS_PT, start=1)
    )

    storage_key = _storage_key(year)
    weekday_icons_storage_key = _weekday_icons_storage_key(year)
    custom_stays_key = _custom_stays_storage_key(year)
    listing_colors_json = json.dumps(LISTING_COLORS)
    month_ids_json = json.dumps([m.lower() for m in MONTHS_PT])
    vapid_key = vapid_public_key()
    vapid_key_json = json.dumps(vapid_key)
    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="{PWA_SPLASH_BACKGROUND}">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="Estadias">
  <link rel="manifest" href="{pwa_manifest_url()}">
  <link rel="icon" href="{pwa_icon_url(192)}" sizes="192x192" type="image/png">
  <link rel="icon" href="{pwa_icon_url(512)}" sizes="512x512" type="image/png">
  <link rel="apple-touch-icon" href="{pwa_icon_url(192)}" sizes="192x192">
  <link rel="apple-touch-icon" href="{pwa_icon_url(512)}" sizes="512x512">
  <title>Mapa de Estadias {year}</title>
  <style>{_CSS}</style>
</head>
<body data-year="{year}">
  <header>
    <h1><button type="button" class="page-title-btn" id="page-title-btn">Mapa de Estadias {year}</button></h1>
    <div class="push-subscribe">
      <button type="button" class="push-subscribe-btn" id="push-subscribe-btn">Ativar notificações</button>
      <div class="push-subscribe-panel" id="push-subscribe-panel" hidden>
        <p class="push-subscribe-hint" id="push-subscribe-hint">
          Copie o JSON abaixo para o secret <code>PUSH_SUBSCRIPTIONS</code> no GitHub (um objeto por telefone).
        </p>
        <textarea id="push-subscription-json" readonly hidden></textarea>
        <div class="push-subscribe-actions">
          <button type="button" class="primary" id="push-subscribe-enable" hidden>Subscrever</button>
          <button type="button" id="push-subscription-copy" hidden>Copiar JSON</button>
        </div>
      </div>
    </div>
  </header>
  <nav class="month-nav" aria-label="Meses">{nav_links}</nav>
  <main>
{months_html}
  </main>
  <div class="comment-backdrop" id="comment-backdrop" hidden>
    <div class="comment-dialog" role="dialog" aria-labelledby="comment-title">
      <div class="comment-dialog-header">
        <h3 id="comment-title">Nota</h3>
        <p class="meta" id="comment-meta"></p>
      </div>
      <textarea id="comment-input" placeholder="Notas para este dia…"></textarea>
      <div class="comment-actions">
        <button type="button" class="danger icon-btn" id="comment-delete-stay" hidden title="Apagar estadia" aria-label="Apagar estadia">{_ICON_BED}</button>
        <button type="button" class="danger icon-btn" id="comment-delete" title="Apagar nota" aria-label="Apagar nota">{_ICON_TRASH}</button>
        <button type="button" class="icon-btn" id="comment-cancel" title="Cancelar" aria-label="Cancelar">{_ICON_X}</button>
        <button type="button" class="primary icon-btn" id="comment-save" title="Guardar" aria-label="Guardar">{_ICON_CHECK}</button>
      </div>
    </div>
  </div>
  <div class="comment-backdrop" id="custom-stay-backdrop" hidden>
    <div class="comment-dialog" role="dialog" aria-labelledby="custom-stay-title">
      <div class="comment-dialog-header">
        <h3 id="custom-stay-title">Nova estadia</h3>
        <p class="meta" id="custom-stay-meta"></p>
      </div>
      <input id="custom-stay-guest" type="text" placeholder="Hóspedes (opcional, ex: 2a)">
      <div class="comment-actions">
        <button type="button" class="icon-btn" id="custom-stay-cancel" title="Cancelar" aria-label="Cancelar">{_ICON_X}</button>
        <button type="button" class="primary icon-btn" id="custom-stay-create" title="Criar estadia" aria-label="Criar estadia">{_ICON_PLUS}</button>
      </div>
    </div>
  </div>
  <div class="comment-backdrop" id="saidas-backdrop" hidden>
    <div class="comment-dialog saidas-dialog" role="dialog" aria-labelledby="saidas-title">
      <div class="comment-dialog-header">
        <h3 id="saidas-title">Saídas</h3>
      </div>
      <pre class="saidas-text" id="saidas-text">{saidas_pre}</pre>
    </div>
  </div>
  <button type="button" class="custom-stay-add" id="custom-stay-add" hidden aria-label="Criar estadia">+</button>
  <button type="button" class="scroll-today-btn" id="scroll-today-btn" title="Ir para hoje" aria-label="Ir para hoje">{_ICON_TODAY}</button>
  <div class="comment-peek" id="comment-peek" hidden role="tooltip">
    <p id="comment-peek-text"></p>
  </div>
  <script>
(function () {{
  const STORAGE_KEY = {storage_key!r};
  const CUSTOM_STAYS_KEY = {custom_stays_key!r};
  const LISTING_COLORS = {listing_colors_json};
  const CUSTOM_STAY_COLOR = {CUSTOM_STAY_COLOR!r};
  const AIRBNB_STAY_URL = {AIRBNB_STAY_URL!r};
  const MONTH_IDS = {month_ids_json};
  const LONG_PRESS_MS = 500;
  let activeCellId = null;
  let longPressTriggered = false;
  let selectionState = null;

  function loadComments() {{
    try {{
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}");
    }} catch (_err) {{
      return {{}};
    }}
  }}

  function saveComments(comments) {{
    localStorage.setItem(STORAGE_KEY, JSON.stringify(comments));
  }}

  function loadCustomStays() {{
    try {{
      return JSON.parse(localStorage.getItem(CUSTOM_STAYS_KEY) || "[]");
    }} catch (_err) {{
      return [];
    }}
  }}

  function saveCustomStays(stays) {{
    localStorage.setItem(CUSTOM_STAYS_KEY, JSON.stringify(stays));
  }}

  function formatIso(dateValue) {{
    return dateValue.slice(0, 4) + "-" + dateValue.slice(4, 6) + "-" + dateValue.slice(6, 8);
  }}

  function compareDates(a, b) {{
    return a.localeCompare(b);
  }}

  function addDays(dateValue, days) {{
    const year = Number(dateValue.slice(0, 4));
    const month = Number(dateValue.slice(4, 6)) - 1;
    const day = Number(dateValue.slice(6, 8));
    const dt = new Date(year, month, day);
    dt.setDate(dt.getDate() + days);
    return (
      String(dt.getFullYear()) +
      String(dt.getMonth() + 1).padStart(2, "0") +
      String(dt.getDate()).padStart(2, "0")
    );
  }}

  function emptySlotSelector(listing, dateValue) {{
    return (
      '.empty-slot[data-listing="' + listing + '"][data-date="' + dateValue + '"]'
    );
  }}

  function getEmptySlot(listing, dateValue) {{
    return document.querySelector(emptySlotSelector(listing, dateValue));
  }}

  function collectContinuousEmptyCells(listing, startDate, endDate) {{
    const start = compareDates(startDate, endDate) <= 0 ? startDate : endDate;
    const end = compareDates(startDate, endDate) <= 0 ? endDate : startDate;
    const cells = [];
    let current = start;
    while (compareDates(current, end) <= 0) {{
      const cell = getEmptySlot(listing, current);
      if (!cell) return null;
      cells.push(cell);
      current = addDays(current, 1);
    }}
    return cells;
  }}

  function clearSelectionHighlight() {{
    document.querySelectorAll(".empty-slot.slot-selected").forEach((cell) => {{
      cell.classList.remove("slot-selected");
    }});
  }}

  const customStayAdd = document.getElementById("custom-stay-add");

  function clearSelection() {{
    clearSelectionHighlight();
    customStayAdd.hidden = true;
    selectionState = null;
  }}

  function isContiguousSelection(cells) {{
    if (cells.length <= 1) return true;
    const listing = cells[0].dataset.listing;
    const dates = cells.map((cell) => cell.dataset.date).sort();
    for (let index = 1; index < dates.length; index += 1) {{
      if (addDays(dates[index - 1], 1) !== dates[index]) return false;
    }}
    return cells.every((cell) => cell.dataset.listing === listing);
  }}

  function largestContiguousSubset(cells) {{
    if (cells.length === 0) return [];
    const sorted = cells
      .slice()
      .sort((left, right) => compareDates(left.dataset.date, right.dataset.date));
    let best = [sorted[0]];
    let current = [sorted[0]];
    for (let index = 1; index < sorted.length; index += 1) {{
      if (addDays(sorted[index - 1].dataset.date, 1) === sorted[index].dataset.date) {{
        current.push(sorted[index]);
      }} else {{
        if (current.length > best.length) best = current;
        current = [sorted[index]];
      }}
    }}
    return current.length > best.length ? current : best;
  }}

  function applySelectionCells(cells) {{
    clearSelectionHighlight();
    if (!cells.length || !isContiguousSelection(cells)) {{
      clearSelection();
      return;
    }}
    const sorted = cells
      .slice()
      .sort((left, right) => compareDates(left.dataset.date, right.dataset.date));
    sorted.forEach((cell) => cell.classList.add("slot-selected"));
    selectionState = {{
      listing: sorted[0].dataset.listing,
      startDate: sorted[0].dataset.date,
      endDate: sorted[sorted.length - 1].dataset.date,
      cells: sorted,
    }};
    positionAddButton(sorted);
  }}

  function getSelectedEmptySlots() {{
    return Array.from(document.querySelectorAll(".empty-slot.slot-selected"));
  }}

  function toggleEmptySlotSelection(cell) {{
    const listing = cell.dataset.listing;
    const dateValue = cell.dataset.date;

    if (cell.classList.contains("slot-selected")) {{
      const remaining = getSelectedEmptySlots().filter((slot) => slot !== cell);
      if (remaining.length === 0) {{
        clearSelection();
        return;
      }}
      applySelectionCells(
        isContiguousSelection(remaining) ? remaining : largestContiguousSubset(remaining)
      );
      return;
    }}

    const selected = getSelectedEmptySlots();
    if (selected.length === 0) {{
      applySelectionCells([cell]);
      return;
    }}
    if (selected[0].dataset.listing !== listing) {{
      applySelectionCells([cell]);
      return;
    }}

    const dates = selected.map((slot) => slot.dataset.date).sort();
    const startDate = dates[0];
    const endDate = dates[dates.length - 1];
    if (dateValue === addDays(startDate, -1) || dateValue === addDays(endDate, 1)) {{
      applySelectionCells([...selected, cell]);
      return;
    }}

    applySelectionCells([cell]);
  }}

  function positionAddButton(cells) {{
    const lastCell = cells[cells.length - 1];
    const rect = lastCell.getBoundingClientRect();
    customStayAdd.hidden = false;
    const btnW = customStayAdd.offsetWidth;
    const btnH = customStayAdd.offsetHeight;
    const grid = lastCell.closest(".grid");
    const gridGap = grid
      ? Number.parseFloat(getComputedStyle(grid).columnGap || getComputedStyle(grid).gap) || 2
      : 2;
    const cellClearance = rect.width + gridGap;
    let left = rect.right + cellClearance;
    let top = rect.top + rect.height / 2 - btnH / 2;
    if (left + btnW > window.innerWidth - 8) {{
      left = rect.left + rect.width / 2 - btnW / 2;
      top = rect.bottom + 6;
    }}
    if (top + btnH > window.innerHeight - 8) {{
      top = rect.top - btnH - 6;
    }}
    left = Math.max(8, Math.min(left, window.innerWidth - btnW - 8));
    top = Math.max(8, Math.min(top, window.innerHeight - btnH - 8));
    customStayAdd.style.left = left + "px";
    customStayAdd.style.top = top + "px";
  }}

  function bindEmptySlotLongPress(cell) {{
    if (cell.dataset.slotBound === "true") return;
    cell.dataset.slotBound = "true";
    let pressTimer = null;

    const clearPress = () => {{
      if (pressTimer !== null) {{
        window.clearTimeout(pressTimer);
        pressTimer = null;
      }}
    }};

    const startPress = () => {{
      if (!cell.classList.contains("empty-slot")) return;
      clearPress();
      pressTimer = window.setTimeout(() => {{
        pressTimer = null;
        toggleEmptySlotSelection(cell);
      }}, LONG_PRESS_MS);
    }};

    const endPress = () => {{
      clearPress();
    }};

    cell.addEventListener("touchstart", startPress, {{ passive: true }});
    cell.addEventListener("touchend", endPress);
    cell.addEventListener("touchmove", clearPress);
    cell.addEventListener("touchcancel", endPress);
    cell.addEventListener("mousedown", (event) => {{
      if (event.button !== 0) return;
      startPress();
    }});
    cell.addEventListener("mouseup", endPress);
    cell.addEventListener("mouseleave", endPress);
  }}

  function initEmptySlotSelection() {{
    document.querySelectorAll(".empty-slot").forEach(bindEmptySlotLongPress);
    document.addEventListener("click", (event) => {{
      if (
        event.target.closest(".empty-slot") ||
        event.target.closest("#custom-stay-add") ||
        event.target.closest("#custom-stay-backdrop") ||
        event.target.closest(".custom-stay-add")
      ) {{
        return;
      }}
      clearSelection();
    }});
    document.addEventListener("keydown", (event) => {{
      if (event.key === "Escape") {{
        clearSelection();
        closeCustomStayDialog();
      }}
    }});
  }}

  function stayTitle(listing, startDate, endDate, guestLabel, isCustom) {{
    let title = listing + ": " + formatIso(startDate) + " → " + formatIso(endDate);
    if (isCustom) title += " (personalizada)";
    if (guestLabel) title += " | Hóspedes: " + guestLabel;
    return title;
  }}

  function bindStayCell(cell) {{
    if (cell.dataset.stayBound === "true") return;
    cell.dataset.stayBound = "true";
    bindLongPress(cell);
    cell.addEventListener("click", (event) => {{
      if (longPressTriggered) {{
        event.preventDefault();
        longPressTriggered = false;
        return;
      }}
      openDialog(cell);
    }});
    cell.addEventListener("keydown", (event) => {{
      if (event.key === "Enter" || event.key === " ") {{
        event.preventDefault();
        openDialog(cell);
      }}
    }});
  }}

  function initCommentCells() {{
    document.querySelectorAll(".stay-comment, .day-comment").forEach(bindStayCell);
  }}

  function removeStayLabelMask(maskKey) {{
    document
      .querySelectorAll('.stay-label-mask[data-stay-label-key="' + maskKey + '"]')
      .forEach((el) => el.remove());
  }}

  function layoutStayLabelMask(maskKey, label, cells) {{
    removeStayLabelMask(maskKey);
    if (!label || cells.length === 0) return;

    const grid = cells[0].closest(".grid");
    if (!grid) return;

    const inGrid = cells.filter((cell) => cell.closest(".grid") === grid);
    if (inGrid.length === 0) return;

    const first = inGrid[0];
    const last = inGrid[inGrid.length - 1];
    const mask = document.createElement("div");
    mask.className = "stay-label-mask";
    mask.dataset.stayLabelKey = maskKey;
    const labelEl = document.createElement("span");
    labelEl.className = "stay-label";
    labelEl.textContent = label;
    mask.appendChild(labelEl);
    mask.style.left = first.offsetLeft + "px";
    mask.style.top = first.offsetTop + "px";
    mask.style.width = last.offsetLeft + last.offsetWidth - first.offsetLeft + "px";
    mask.style.height = first.offsetHeight + "px";
    grid.appendChild(mask);
  }}

  function layoutCustomStayLabelMask(stay, cells) {{
    layoutStayLabelMask("custom:" + stay.id, stay.guestLabel, cells);
  }}

  function layoutAirbnbStayLabelsInGrid(grid) {{
    const keys = new Set();
    grid.querySelectorAll(".stay-comment:not(.stay-custom)[data-stay-key]").forEach((cell) => {{
      keys.add(cell.dataset.stayKey);
    }});
    keys.forEach((key) => {{
      const cells = Array.from(
        grid.querySelectorAll('.stay-comment[data-stay-key="' + key + '"]')
      )
        .filter(
          (cell) =>
            !cell.classList.contains("stay-custom") && cell.closest(".grid") === grid
        )
        .sort((left, right) => compareDates(left.dataset.date, right.dataset.date));
      const labelCell = cells.find((cell) => cell.dataset.guestLabel);
      const label = labelCell ? labelCell.dataset.guestLabel : "";
      layoutStayLabelMask("airbnb:" + key, label, cells);
    }});
  }}

  function layoutAirbnbStayLabels() {{
    document.querySelectorAll(".month-scroll .grid").forEach(layoutAirbnbStayLabelsInGrid);
  }}

  function relayoutAllStayLabels() {{
    document.querySelectorAll(".stay-label-mask").forEach((el) => el.remove());
    layoutAirbnbStayLabels();
    loadCustomStays().forEach((stay) => {{
      const cells = Array.from(
        document.querySelectorAll('[data-custom-stay="' + stay.id + '"]')
      );
      if (cells.length) layoutStayLabelMask("custom:" + stay.id, stay.guestLabel, cells);
    }});
  }}

  function nextStayCell(listing, dateValue) {{
    return document.querySelector(
      '.stay-comment[data-listing="' + listing + '"][data-date="' + addDays(dateValue, 1) + '"]'
    );
  }}

  function stayKeyForCell(cell) {{
    return cell.dataset.stayKey || cell.dataset.customStay || "";
  }}

  function markStayEndCell(cell) {{
    cell.classList.add("stay-end");
    cell.classList.toggle("weekend-end", cell.dataset.weekend === "true");
  }}

  function refreshStayEndGradients() {{
    document.querySelectorAll(".listing-row.stay.stay-comment").forEach((cell) => {{
      cell.classList.remove("stay-end", "weekend-end");
    }});
    document.querySelectorAll(".listing-row.stay.stay-comment").forEach((cell) => {{
      const next = nextStayCell(cell.dataset.listing, cell.dataset.date);
      if (!next) {{
        markStayEndCell(cell);
        return;
      }}
      const currentKey = stayKeyForCell(cell);
      const nextKey = stayKeyForCell(next);
      if (currentKey && nextKey && currentKey !== nextKey) {{
        markStayEndCell(cell);
      }}
    }});
  }}

  function relayoutAllCustomStayLabels() {{
    relayoutAllStayLabels();
  }}

  function paintCustomStay(stay) {{
    const cells = collectContinuousEmptyCells(stay.listing, stay.startDate, stay.endDate);
    if (!cells) return;
    const color = CUSTOM_STAY_COLOR;
    cells.forEach((cell) => {{
      cell.classList.remove(
        "empty-slot",
        "weekend-empty",
        "slot-selected",
        "stay-end"
      );
      cell.classList.add("stay", "stay-comment", "stay-custom");
      cell.style.removeProperty("background");
      cell.style.setProperty("--stay-color", color);
      cell.dataset.customStay = stay.id;
      cell.dataset.stayKey = stay.id;
      cell.setAttribute("role", "button");
      cell.tabIndex = 0;
      cell.replaceChildren();
      cell.title = stayTitle(
        stay.listing,
        stay.startDate,
        stay.endDate,
        stay.guestLabel || "",
        true
      );
      bindStayCell(cell);
    }});
    layoutCustomStayLabelMask(stay, cells);
  }}

  function applyCustomStays() {{
    document.querySelectorAll(".stay-label-mask").forEach((el) => el.remove());
    loadCustomStays().forEach(paintCustomStay);
    refreshStayEndGradients();
  }}

  function restoreEmptyCell(cell) {{
    const isWeekend = cell.dataset.weekend === "true";
    cell.className = "cell listing-row empty-slot" + (isWeekend ? " weekend-empty" : "");
    cell.style.removeProperty("background");
    cell.style.removeProperty("--stay-color");
    cell.removeAttribute("role");
    cell.tabIndex = -1;
    cell.textContent = "";
    cell.removeAttribute("title");
    delete cell.dataset.customStay;
    delete cell.dataset.stayKey;
    delete cell.dataset.stayBound;
    delete cell.dataset.slotBound;
    bindEmptySlotLongPress(cell);
  }}

  function customStayHasComment(customStayId) {{
    if (!customStayId) return false;
    const comments = loadComments();
    return Array.from(
      document.querySelectorAll('[data-custom-stay="' + customStayId + '"]')
    ).some((cell) => (comments[cell.id] || "").trim());
  }}

  function deleteCustomStay(customStayId) {{
    if (customStayHasComment(customStayId)) return;
    const stays = loadCustomStays().filter((stay) => stay.id !== customStayId);
    saveCustomStays(stays);
    removeStayLabelMask("custom:" + customStayId);
    document.querySelectorAll('[data-custom-stay="' + customStayId + '"]').forEach((cell) => {{
      restoreEmptyCell(cell);
    }});
    refreshStayEndGradients();
  }}

  function applySavedComments() {{
    const comments = loadComments();
    document.querySelectorAll(".stay-comment, .day-comment").forEach((cell) => {{
      const text = comments[cell.id];
      const hasComment = Boolean(text && text.trim());
      if (!cell.dataset.baseTitle) {{
        cell.dataset.baseTitle = cell.getAttribute("title") || "";
      }}
      cell.classList.toggle("has-comment", hasComment);
      if (cell.classList.contains("day-comment")) {{
        cell.title = hasComment ? "Nota: " + text.trim() : "";
      }} else {{
        cell.title = hasComment
          ? cell.dataset.baseTitle + " | Nota: " + text.trim()
          : cell.dataset.baseTitle;
      }}
    }});
  }}

  const backdrop = document.getElementById("comment-backdrop");
  const meta = document.getElementById("comment-meta");
  const input = document.getElementById("comment-input");
  const deleteStayButton = document.getElementById("comment-delete-stay");
  const commentPeek = document.getElementById("comment-peek");
  const commentPeekText = document.getElementById("comment-peek-text");
  const customStayBackdrop = document.getElementById("custom-stay-backdrop");
  const customStayMeta = document.getElementById("custom-stay-meta");
  const customStayGuest = document.getElementById("custom-stay-guest");
  function commentForCell(cellId) {{
    return (loadComments()[cellId] || "").trim();
  }}

  function positionCommentPeek(cell) {{
    commentPeek.hidden = false;
    commentPeek.style.visibility = "hidden";
    commentPeek.style.left = "0px";
    commentPeek.style.top = "0px";
    const rect = cell.getBoundingClientRect();
    const peek = commentPeek.getBoundingClientRect();
    let left = rect.left + rect.width / 2 - peek.width / 2;
    let top = rect.top - peek.height - 8;
    if (top < 8) {{
      top = rect.bottom + 8;
    }}
    left = Math.max(8, Math.min(left, window.innerWidth - peek.width - 8));
    commentPeek.style.left = left + "px";
    commentPeek.style.top = top + "px";
    commentPeek.style.visibility = "";
  }}

  function showCommentPeek(cell) {{
    const text = commentForCell(cell.id);
    if (!text) return;
    commentPeekText.textContent = text;
    positionCommentPeek(cell);
  }}

  function hideCommentPeek() {{
    commentPeek.hidden = true;
  }}

  function airbnbReservationUrlForCell(cell) {{
    if (!cell.classList.contains("stay") || cell.classList.contains("stay-custom")) {{
      return null;
    }}
    const stayKey = cell.dataset.stayKey || "";
    if (!stayKey || stayKey.includes(":")) {{
      return null;
    }}
    return AIRBNB_STAY_URL + encodeURIComponent(stayKey);
  }}

  function bindLongPress(cell) {{
    let pressTimer = null;

    const clearPress = () => {{
      if (pressTimer !== null) {{
        window.clearTimeout(pressTimer);
        pressTimer = null;
      }}
    }};

    const endPress = () => {{
      clearPress();
      hideCommentPeek();
    }};

    const startPress = () => {{
      const stayUrl = airbnbReservationUrlForCell(cell);
      const hasComment = cell.classList.contains("has-comment");
      if (!stayUrl && !hasComment) return;
      clearPress();
      longPressTriggered = false;
      pressTimer = window.setTimeout(() => {{
        pressTimer = null;
        longPressTriggered = true;
        if (stayUrl) {{
          window.open(stayUrl, "_blank", "noopener,noreferrer");
          return;
        }}
        showCommentPeek(cell);
      }}, LONG_PRESS_MS);
    }};

    cell.addEventListener("touchstart", startPress, {{ passive: true }});
    cell.addEventListener("touchend", endPress);
    cell.addEventListener("touchmove", clearPress);
    cell.addEventListener("touchcancel", endPress);
    cell.addEventListener("mousedown", (event) => {{
      if (event.button !== 0) return;
      startPress();
    }});
    cell.addEventListener("mouseup", endPress);
    cell.addEventListener("mouseleave", endPress);
  }}

  function openDialog(cell) {{
    activeCellId = cell.id;
    const listing = cell.dataset.listing;
    const date = cell.dataset.date;
    meta.textContent = cell.classList.contains("day-comment")
      ? formatIso(date)
      : listing + " · " + formatIso(date);
    input.value = loadComments()[activeCellId] || "";
    deleteStayButton.hidden =
      !cell.classList.contains("stay-custom") ||
      customStayHasComment(cell.dataset.customStay);
    backdrop.hidden = false;
    backdrop.classList.add("open");
    input.focus();
  }}

  function closeDialog() {{
    backdrop.classList.remove("open");
    backdrop.hidden = true;
    activeCellId = null;
    deleteStayButton.hidden = true;
  }}

  function openCustomStayDialog() {{
    if (!selectionState) return;
    customStayMeta.textContent =
      selectionState.listing +
      " · " +
      formatIso(selectionState.startDate) +
      " → " +
      formatIso(selectionState.endDate);
    customStayGuest.value = "";
    customStayBackdrop.hidden = false;
    customStayBackdrop.classList.add("open");
    customStayGuest.focus();
  }}

  function closeCustomStayDialog() {{
    customStayBackdrop.classList.remove("open");
    customStayBackdrop.hidden = true;
  }}

  function createCustomStay() {{
    if (!selectionState) return;
    const stay = {{
      id: "cs-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7),
      listing: selectionState.listing,
      startDate: selectionState.startDate,
      endDate: selectionState.endDate,
      guestLabel: customStayGuest.value.trim(),
    }};
    const stays = loadCustomStays();
    stays.push(stay);
    saveCustomStays(stays);
    paintCustomStay(stay);
    applySavedComments();
    closeCustomStayDialog();
    clearSelection();
  }}

  customStayAdd.addEventListener("pointerup", (event) => {{
    event.preventDefault();
    event.stopPropagation();
    openCustomStayDialog();
  }});

  document.getElementById("custom-stay-cancel").addEventListener("click", closeCustomStayDialog);
  customStayBackdrop.addEventListener("click", (event) => {{
    if (event.target === customStayBackdrop) closeCustomStayDialog();
  }});
  document.getElementById("custom-stay-create").addEventListener("click", createCustomStay);

  document.getElementById("comment-cancel").addEventListener("click", closeDialog);
  backdrop.addEventListener("click", (event) => {{
    if (event.target === backdrop) closeDialog();
  }});

  document.getElementById("comment-save").addEventListener("click", () => {{
    if (!activeCellId) return;
    const comments = loadComments();
    const text = input.value.trim();
    if (text) {{
      comments[activeCellId] = text;
    }} else {{
      delete comments[activeCellId];
    }}
    saveComments(comments);
    applySavedComments();
    closeDialog();
  }});

  document.getElementById("comment-delete").addEventListener("click", () => {{
    if (!activeCellId) return;
    const comments = loadComments();
    delete comments[activeCellId];
    saveComments(comments);
    input.value = "";
    applySavedComments();
    closeDialog();
  }});

  deleteStayButton.addEventListener("click", () => {{
    if (!activeCellId) return;
    const cell = document.getElementById(activeCellId);
    const customStayId = cell && cell.dataset.customStay;
    if (!customStayId || customStayHasComment(customStayId)) return;
    deleteCustomStay(customStayId);
    closeDialog();
  }});

  applyCustomStays();
  layoutAirbnbStayLabels();
  initCommentCells();
  initEmptySlotSelection();
  applySavedComments();

  const WEEKDAY_ICONS_STORAGE_KEY = {weekday_icons_storage_key!r};
  const PLANE_ICON = "\u2708\ufe0f";
  const PALM_ICON = "\U0001f334";
  const SPONGE_ICON = "\U0001f9fd";
  const HOLIDAY_ICON = "{HOLIDAY_ICON}";
  const WEEKDAY_ICONS = {{
    plane: PLANE_ICON,
    palm: PALM_ICON,
    sponge: SPONGE_ICON,
  }};

  function loadWeekdayIcons() {{
    try {{
      return JSON.parse(localStorage.getItem(WEEKDAY_ICONS_STORAGE_KEY) || "{{}}");
    }} catch (_err) {{
      return {{}};
    }}
  }}

  function saveWeekdayIcons(icons) {{
    localStorage.setItem(WEEKDAY_ICONS_STORAGE_KEY, JSON.stringify(icons));
  }}

  function defaultWeekdayHeader(cell) {{
    const letter = cell.dataset.default;
    cell.dataset.iconState = "default";
    cell.classList.remove("has-icon");
    if (cell.classList.contains("has-holiday")) {{
      cell.innerHTML =
        '<span class="holiday-marker" aria-hidden="true">' + HOLIDAY_ICON + '</span>';
    }} else {{
      cell.innerHTML = '<span class="weekday-letter">' + letter + '</span>';
    }}
  }}

  function setWeekdayIcon(cell, state) {{
    cell.dataset.iconState = state;
    cell.classList.add("has-icon");
    cell.textContent = WEEKDAY_ICONS[state];
  }}

  function applyWeekdayIconState(cell, state) {{
    if (state === "default") {{
      defaultWeekdayHeader(cell);
    }} else {{
      setWeekdayIcon(cell, state);
    }}
  }}

  function persistWeekdayIconState(cell) {{
    if (!cell.id) return;
    const icons = loadWeekdayIcons();
    const state = cell.dataset.iconState || "default";
    if (state === "default") {{
      delete icons[cell.id];
    }} else {{
      icons[cell.id] = state;
    }}
    saveWeekdayIcons(icons);
  }}

  function applySavedWeekdayIcons() {{
    const icons = loadWeekdayIcons();
    document.querySelectorAll(".weekday-header").forEach((cell) => {{
      if (!cell.id) return;
      let saved = icons[cell.id];
      if (saved === "bucket") saved = "sponge";
      if (saved && saved !== "default" && WEEKDAY_ICONS[saved]) {{
        applyWeekdayIconState(cell, saved);
      }} else if (!cell.dataset.iconState) {{
        cell.dataset.iconState = "default";
      }}
    }});
  }}

  document.querySelectorAll(".weekday-header").forEach((cell) => {{
    if (!cell.dataset.iconState) {{
      cell.dataset.iconState = "default";
    }}
    cell.addEventListener("dblclick", () => {{
      const state = cell.dataset.iconState || "default";
      if (state === "default") {{
        setWeekdayIcon(cell, "plane");
      }} else if (state === "plane") {{
        setWeekdayIcon(cell, "palm");
      }} else if (state === "palm") {{
        setWeekdayIcon(cell, "sponge");
      }} else {{
        defaultWeekdayHeader(cell);
      }}
      persistWeekdayIconState(cell);
    }});
  }});
  applySavedWeekdayIcons();

  const scrollTodayBtn = document.getElementById("scroll-today-btn");

  function markToday() {{
    const now = new Date();
    const y = String(now.getFullYear());
    const m = String(now.getMonth() + 1).padStart(2, "0");
    const d = String(now.getDate()).padStart(2, "0");
    const todayStr = y + m + d;
    const cell = document.querySelector('.day-num[data-date="' + todayStr + '"]');
    if (cell) {{
      cell.classList.add("is-today");
    }} else if (scrollTodayBtn) {{
      scrollTodayBtn.hidden = true;
    }}
  }}

  function centerTodayHorizontally() {{
    const todayCell = document.querySelector(".cell.day-num.is-today");
    if (!todayCell) return;
    const scrollEl = todayCell.closest(".month-scroll");
    if (!scrollEl) return;

    const containerRect = scrollEl.getBoundingClientRect();
    const cellRect = todayCell.getBoundingClientRect();
    const delta =
      cellRect.left + cellRect.width / 2
      - (containerRect.left + containerRect.width / 2);
    const target = scrollEl.scrollLeft + delta;
    const maxScroll = scrollEl.scrollWidth - scrollEl.clientWidth;
    scrollEl.scrollLeft = Math.max(0, Math.min(target, maxScroll));
  }}

  function scrollTodayIntoCenter() {{
    if (!window.matchMedia("(max-width: 768px)").matches) return;
    centerTodayHorizontally();
  }}

  function scrollToCurrentMonth(behavior) {{
    const pageYear = Number(document.body.dataset.year);
    const now = new Date();
    const currentYear = now.getFullYear();
    let monthIndex;
    if (pageYear === currentYear) {{
      monthIndex = now.getMonth();
    }} else if (pageYear < currentYear) {{
      monthIndex = 11;
    }} else {{
      monthIndex = 0;
    }}
    const section = document.getElementById(MONTH_IDS[monthIndex]);
    if (section) {{
      section.scrollIntoView({{ behavior: behavior, block: "start" }});
    }}
  }}

  function scrollToInitialMonth() {{
    if (window.location.hash) return;
    scrollToCurrentMonth("instant");
  }}

  function goToToday() {{
    if (!document.querySelector(".cell.day-num.is-today")) return;
    scrollToCurrentMonth("smooth");
    requestAnimationFrame(() => {{
      requestAnimationFrame(centerTodayHorizontally);
    }});
  }}

  if (scrollTodayBtn) {{
    scrollTodayBtn.addEventListener("click", goToToday);
  }}

  const saidasBackdrop = document.getElementById("saidas-backdrop");
  const pageTitle = document.getElementById("page-title-btn");

  function openSaidasDialog() {{
    saidasBackdrop.hidden = false;
    saidasBackdrop.classList.add("open");
  }}

  function closeSaidasDialog() {{
    saidasBackdrop.classList.remove("open");
    saidasBackdrop.hidden = true;
  }}

  if (pageTitle && saidasBackdrop) {{
    pageTitle.addEventListener("click", openSaidasDialog);
    saidasBackdrop.addEventListener("click", (event) => {{
      if (event.target === saidasBackdrop) closeSaidasDialog();
    }});
  }}

  function runInitialScroll() {{
    scrollToInitialMonth();
    requestAnimationFrame(() => {{
      requestAnimationFrame(scrollTodayIntoCenter);
    }});
  }}

  let customStayLabelLayoutTimer = null;
  window.addEventListener("resize", () => {{
    if (customStayLabelLayoutTimer !== null) {{
      window.clearTimeout(customStayLabelLayoutTimer);
    }}
    customStayLabelLayoutTimer = window.setTimeout(() => {{
      customStayLabelLayoutTimer = null;
      relayoutAllCustomStayLabels();
      scrollTodayIntoCenter();
    }}, 120);
  }});

  markToday();
  runInitialScroll();
}})();
  </script>
  <script>
(function () {{
  const VAPID_PUBLIC_KEY = {vapid_key_json};
  const pushSubscribeBtn = document.getElementById("push-subscribe-btn");
  const pushSubscribePanel = document.getElementById("push-subscribe-panel");
  const pushSubscribeHint = document.getElementById("push-subscribe-hint");
  const pushSubscribeEnable = document.getElementById("push-subscribe-enable");
  const pushSubscriptionJson = document.getElementById("push-subscription-json");
  const pushSubscriptionCopy = document.getElementById("push-subscription-copy");

  function urlBase64ToUint8Array(base64String) {{
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(base64);
    const output = new Uint8Array(raw.length);
    for (let index = 0; index < raw.length; index += 1) {{
      output[index] = raw.charCodeAt(index);
    }}
    return output;
  }}

  function subscriptionToJson(subscription) {{
    const json = subscription.toJSON();
    return JSON.stringify({{
      endpoint: json.endpoint,
      keys: json.keys,
    }}, null, 2);
  }}

  async function ensureServiceWorker() {{
    if (!("serviceWorker" in navigator)) {{
      throw new Error("Service worker indisponível.");
    }}
    return navigator.serviceWorker.ready;
  }}

  async function refreshPushSubscription() {{
    const registration = await ensureServiceWorker();
    const subscription = await registration.pushManager.getSubscription();
    if (!subscription) {{
      return null;
    }}
    pushSubscriptionJson.value = subscriptionToJson(subscription);
    pushSubscriptionJson.hidden = false;
    pushSubscriptionCopy.hidden = false;
    pushSubscribeHint.textContent =
      "Subscrição ativa. Copie o JSON para PUSH_SUBSCRIPTIONS no GitHub.";
    return subscription;
  }}

  async function subscribeToPush() {{
    const registration = await ensureServiceWorker();
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {{
      throw new Error("Permissão de notificações negada.");
    }}
    const subscription = await registration.pushManager.subscribe({{
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
    }});
    pushSubscriptionJson.value = subscriptionToJson(subscription);
    pushSubscriptionJson.hidden = false;
    pushSubscriptionCopy.hidden = false;
    pushSubscribeHint.textContent =
      "Subscrição criada. Copie o JSON para PUSH_SUBSCRIPTIONS no GitHub.";
    return subscription;
  }}

  function initPushSubscribe() {{
    if (!pushSubscribeBtn) {{
      return;
    }}
    const pushAvailable =
      "serviceWorker" in navigator &&
      "PushManager" in window &&
      "Notification" in window;
    if (!pushAvailable) {{
      pushSubscribeBtn.disabled = true;
      pushSubscribeBtn.textContent = "Notificações indisponíveis";
      return;
    }}
    if (!VAPID_PUBLIC_KEY) {{
      pushSubscribeBtn.disabled = true;
      pushSubscribeBtn.textContent = "Notificações não configuradas";
      return;
    }}

    pushSubscribeBtn.addEventListener("click", () => {{
      const open = !pushSubscribePanel.hidden;
      pushSubscribePanel.hidden = open;
    }});

    pushSubscribeEnable.hidden = false;
    pushSubscribeEnable.addEventListener("click", () => {{
      subscribeToPush().catch((error) => {{
        window.alert(error.message || "Não foi possível subscrever.");
      }});
    }});

    pushSubscriptionCopy.addEventListener("click", async () => {{
      const text = pushSubscriptionJson.value;
      if (!text) {{
        return;
      }}
      try {{
        await navigator.clipboard.writeText(text);
        pushSubscriptionCopy.textContent = "Copiado";
        window.setTimeout(() => {{
          pushSubscriptionCopy.textContent = "Copiar JSON";
        }}, 1500);
      }} catch (_error) {{
        pushSubscriptionJson.focus();
        pushSubscriptionJson.select();
      }}
    }});

    refreshPushSubscription().catch(() => {{}});
  }}

  initPushSubscribe();
}})();
  </script>
  <script>
if ("serviceWorker" in navigator) {{
  navigator.serviceWorker.register({pwa_sw_url()!r}, {{
    scope: "/airbnb/",
    updateViaCache: "none",
  }}).catch(() => {{}});
}}
  </script>
</body>
</html>
"""


def write_calendar_html(
    *,
    year: int,
    bookings: list[dict],
    output_path: Path,
    upcoming_checkouts_text: str | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_calendar_html(
            year=year,
            bookings=bookings,
            upcoming_checkouts_text=upcoming_checkouts_text,
        ),
        encoding="utf-8",
    )
    return output_path
