#!/usr/bin/env python3
"""Fetch Airbnb multicalendar bookings into shared/bookings.json."""

from __future__ import annotations

import argparse

from fetch.run_fetch import add_fetch_arguments, run_fetch_from_namespace


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python fetch/main.py",
        description=(
            "Open Chrome with the persistent calendar-airbnb profile, navigate "
            "to the Airbnb multicalendar, and write shared/bookings.json.\n\n"
            "Flow:\n"
            "  1. Open Chrome (persistent profile calendar-airbnb)\n"
            "  2. Navigate to https://www.airbnb.pt/multicalendar\n"
            "  3. Accept cookies if prompted\n"
            "  4. Log in to Airbnb if not already authenticated\n"
            "  5. Extract bookings for the next 3 months into shared/bookings.json\n\n"
            "Chrome closes when finished. Runs headless by default; pass --gui for a visible browser.\n\n"
            "Prerequisites:\n"
            "  • credentials.local.env with AIRBNB_EMAIL and AIRBNB_PASSWORD"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_fetch_arguments(parser)
    args = parser.parse_args()
    run_fetch_from_namespace(args)


if __name__ == "__main__":
    main()
