#!/usr/bin/env python3
"""Build the annual cleaning calendar HTML from bookings.json."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import date
from pathlib import Path

from cleanings.booking_helpers import year_from_bookings
from cleanings.html_export import write_cleaning_html
from fetch.run_fetch import add_fetch_arguments, maybe_run_fetch
from shared.paths import bookings_json_path, project_root

CLEANINGS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = project_root()
DEFAULT_BOOKINGS = bookings_json_path()
DEFAULT_OUTPUT_DIR = CLEANINGS_DIR / "templates"
DOCS_INDEX = PROJECT_ROOT / "docs" / "index.html"


def build_cleaning_html(
    bookings_path: Path = DEFAULT_BOOKINGS,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[int, Path]:
    data = json.loads(bookings_path.read_text(encoding="utf-8"))
    year = year_from_bookings(data)
    bookings = data.get("bookings", [])
    html_path = output_dir / f"cleanings-{year}.html"
    write_cleaning_html(year=year, bookings=bookings, output_path=html_path)
    if output_dir.resolve() == DEFAULT_OUTPUT_DIR.resolve():
        DOCS_INDEX.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(html_path, DOCS_INDEX)
    return year, html_path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python cleanings/main.py",
        description=(
            "Write cleanings/templates/cleanings-{year}.html from "
            "shared/bookings.json.\n\n"
            "Fetches shared/bookings.json from Airbnb by default for the full "
            "calendar year. Pass --no-fetch to reuse an existing file."
        ),
    )
    add_fetch_arguments(parser, offer_no_fetch=True, include_range_args=False)
    parser.add_argument(
        "--year",
        type=int,
        default=date.today().year,
        metavar="YYYY",
        help="Calendar year to fetch from Airbnb (default: current year).",
    )
    parser.add_argument(
        "--bookings",
        type=Path,
        default=DEFAULT_BOOKINGS,
        help=f"Path to bookings.json (default: {DEFAULT_BOOKINGS.relative_to(PROJECT_ROOT)})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=(
            f"Directory for cleanings-{{year}}.html "
            f"(default: {DEFAULT_OUTPUT_DIR.relative_to(PROJECT_ROOT)})"
        ),
    )
    args = parser.parse_args()

    maybe_run_fetch(args, calendar_year=None if args.no_fetch else args.year)

    if not args.bookings.is_file():
        raise SystemExit(
            f"Missing {args.bookings}. Run without --no-fetch or run ./fetch.sh."
        )

    year, html_path = build_cleaning_html(args.bookings, args.output_dir)
    if args.output_dir.resolve() == DEFAULT_OUTPUT_DIR.resolve():
        print(f"Wrote {html_path} and {DOCS_INDEX} for {year}")
    else:
        print(f"Wrote {html_path} for {year}")


if __name__ == "__main__":
    main()
