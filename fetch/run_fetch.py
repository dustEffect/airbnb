"""Shared Airbnb fetch entry point for fetch, checkouts, and cleanings scripts."""

from __future__ import annotations

import argparse
from datetime import date

from airbnb_urls import multicalendar_url
from bookings_extract import MONTHS_AHEAD, parse_start_month
from chrome_profile import open_profile_until_exit


def month_arg(value: str) -> date:
    try:
        return parse_start_month(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def run_fetch(
    *,
    months_ahead: int = MONTHS_AHEAD,
    from_month: date | None = None,
    calendar_year: int | None = None,
    headless: bool = True,
) -> None:
    open_profile_until_exit(
        start_url=multicalendar_url(),
        headless=headless,
        months_ahead=months_ahead,
        from_month=from_month,
        calendar_year=calendar_year,
    )


def add_fetch_arguments(
    parser: argparse.ArgumentParser,
    *,
    offer_no_fetch: bool = False,
    include_range_args: bool = True,
) -> None:
    if offer_no_fetch:
        parser.add_argument(
            "--no-fetch",
            action="store_true",
            help="Skip Airbnb fetch and use existing shared/bookings.json.",
        )
    if include_range_args:
        parser.add_argument(
            "--months",
            type=int,
            default=MONTHS_AHEAD,
            metavar="N",
            help=f"Months ahead to extract when fetching (default: {MONTHS_AHEAD}).",
        )
        parser.add_argument(
            "--from-month",
            type=month_arg,
            default=None,
            metavar="YYYY-MM",
            help="First month to include when fetching (default: today).",
        )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open a visible Chrome window when fetching (default: headless).",
    )


def run_fetch_from_namespace(
    args: argparse.Namespace,
    *,
    calendar_year: int | None = None,
) -> None:
    run_fetch(
        months_ahead=getattr(args, "months", MONTHS_AHEAD),
        from_month=getattr(args, "from_month", None),
        calendar_year=calendar_year,
        headless=not args.gui,
    )


def maybe_run_fetch(
    args: argparse.Namespace,
    *,
    calendar_year: int | None = None,
) -> None:
    if getattr(args, "no_fetch", False):
        return
    run_fetch_from_namespace(args, calendar_year=calendar_year)
