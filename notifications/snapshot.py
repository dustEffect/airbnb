"""Build a slim bookings snapshot for push notifications."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from fetch.bookings_extract import is_accepted_booking_status
from shared.listing_labels import LISTING_LABELS


def _snapshot_entry(booking: dict) -> dict | None:
    listing_name = booking.get("listingName")
    if not listing_name:
        return None
    label = LISTING_LABELS.get(listing_name.strip())
    if not label:
        return None
    start_date = booking.get("startDate")
    end_date = booking.get("endDate")
    if not start_date or not end_date:
        return None
    status = booking.get("status") or booking.get("hostFacingStatus")
    if status is not None and not is_accepted_booking_status(status):
        return None
    return {
        "listing": label,
        "startDate": start_date,
        "endDate": end_date,
        "guestFirstName": booking.get("guestFirstName"),
    }


def build_snapshot(bookings_payload: dict) -> dict:
    generated_at = bookings_payload.get("extractedAt")
    if generated_at is None:
        generated_at = date.today().isoformat()
    entries = []
    for booking in bookings_payload.get("bookings", []):
        entry = _snapshot_entry(booking)
        if entry is not None:
            entries.append(entry)
    entries.sort(key=lambda item: (item["startDate"], item["listing"]))
    return {"generatedAt": generated_at, "bookings": entries}


def write_snapshot(output_path: Path, bookings_payload: dict) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_snapshot(bookings_payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path
