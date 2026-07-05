#!/usr/bin/env python3
"""Send scheduled booking push notifications from a bookings snapshot."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from notifications.format import (
    format_afternoon_notification,
    format_morning_notification,
    format_test_notification,
)
from notifications.push import send_push_notifications

LISBON = ZoneInfo("Europe/Lisbon")


def _load_subscriptions(raw: str) -> list[dict]:
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return parsed
    raise ValueError("PUSH_SUBSCRIPTIONS must be a JSON object or array.")


def _vapid_claims() -> dict[str, str]:
    subject = os.environ.get("VAPID_SUBJECT", "").strip()
    if not subject:
        raise ValueError("Missing VAPID_SUBJECT (e.g. mailto:you@example.com).")
    return {"sub": subject}


def _message_for_kind(
    kind: str,
    *,
    snapshot: dict | None,
    on_date: date,
    now: datetime,
) -> dict[str, str] | None:
    if kind == "test":
        return format_test_notification(now=now)
    if snapshot is None:
        raise ValueError("snapshot is required for morning and afternoon notifications.")
    if kind == "morning":
        return format_morning_notification(snapshot, on_date=on_date)
    return format_afternoon_notification(snapshot, on_date=on_date)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m notifications.main",
        description=(
            "Format and send a booking push notification from docs/bookings-snapshot.json."
        ),
    )
    parser.add_argument(
        "kind",
        choices=("morning", "afternoon", "test"),
        help=(
            "morning = today's check-ins; afternoon = tomorrow's check-ins and "
            "check-outs; test = fixed test message"
        ),
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help="Path to bookings-snapshot.json (not required for test)",
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
        help="Reference date in Europe/Lisbon (default: today in Lisbon)",
    )
    args = parser.parse_args()

    now = datetime.now(LISBON)
    on_date = args.date or now.date()
    snapshot: dict | None = None
    if args.kind != "test":
        if args.snapshot is None or not args.snapshot.is_file():
            path = args.snapshot or Path("docs/bookings-snapshot.json")
            print(f"Missing snapshot: {path}", file=sys.stderr)
            sys.exit(1)
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))

    message = _message_for_kind(args.kind, snapshot=snapshot, on_date=on_date, now=now)
    if message is None:
        print(f"No {args.kind} notification for {on_date.isoformat()}; skipping.")
        return

    subscriptions_raw = os.environ.get("PUSH_SUBSCRIPTIONS", "").strip()
    private_key = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    if not subscriptions_raw or not private_key:
        print(
            "Missing PUSH_SUBSCRIPTIONS or VAPID_PRIVATE_KEY; cannot send push.",
            file=sys.stderr,
        )
        sys.exit(1)

    subscriptions = _load_subscriptions(subscriptions_raw)
    errors = send_push_notifications(
        subscriptions,
        message,
        vapid_private_key=private_key,
        vapid_claims=_vapid_claims(),
    )
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        sys.exit(1)

    print(f"Sent {args.kind} notification for {on_date.isoformat()}.")


if __name__ == "__main__":
    main()
