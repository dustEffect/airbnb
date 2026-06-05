#!/usr/bin/env python3
"""Open Chrome with the persistent profile and the Airbnb multicalendar page."""

from __future__ import annotations

import argparse

from airbnb_calendar.airbnb_urls import multicalendar_url
from airbnb_calendar.chrome_profile import open_profile_until_exit


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description=(
            "Open Chrome with the persistent calendar-airbnb profile and navigate "
            "to the Airbnb multicalendar.\n\n"
            "Flow:\n"
            "  1. Open Chrome (persistent profile calendar-airbnb)\n"
            "  2. Navigate to https://www.airbnb.pt/multicalendar\n"
            "  3. Accept cookies if prompted\n"
            "  4. Log in to Airbnb if not already authenticated\n"
            "  5. Extract bookings for the next 2 months into bookings.json\n"
            "  6. Write checkout summary to bookings.txt and print it to stdout\n\n"
            "Chrome closes when finished. Runs headless by default; pass --gui for a visible browser.\n\n"
            "Prerequisites:\n"
            "  • credentials.local.env with AIRBNB_EMAIL and AIRBNB_PASSWORD"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        dest="diff_checkouts",
        help=(
            "Recalculate bookings but print only checkout row differences to stdout "
            "compared with the current bookings.txt (does not overwrite bookings.txt)."
        ),
    )
    parser.add_argument(
        "--months",
        type=int,
        default=2,
        metavar="N",
        help="Number of months ahead to extract (default: 2).",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open a visible Chrome window (default: headless).",
    )
    args = parser.parse_args()
    url = multicalendar_url()
    open_profile_until_exit(
        start_url=url,
        diff_checkouts=args.diff_checkouts,
        headless=not args.gui,
        months_ahead=args.months,
    )


if __name__ == "__main__":
    main()
