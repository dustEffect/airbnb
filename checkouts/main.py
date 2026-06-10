#!/usr/bin/env python3
"""Build checkouts/checkouts.txt from shared/bookings.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from checkouts.checkouts_format import (
    DIFF_SECTION_HEADER,
    SUMMARY_SECTION_HEADER,
    print_checkouts_diff_from_payload,
    write_checkouts_text,
)
from fetch.run_fetch import add_fetch_arguments, maybe_run_fetch
from shared.paths import bookings_json_path, project_root


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python checkouts/main.py",
        description=(
            "Fetch shared/bookings.json from Airbnb (by default), then write the "
            "checkout summary to checkouts/checkouts.txt and print it to stdout.\n\n"
            "Pass --no-fetch to reuse an existing shared/bookings.json."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_fetch_arguments(parser, offer_no_fetch=True)
    parser.add_argument(
        "--diff",
        action="store_true",
        dest="diff_checkouts",
        help=(
            "Print checkout row differences to stdout (from tomorrow onward only), "
            "then update checkouts/checkouts.txt with the full recalculated summary."
        ),
    )
    parser.add_argument(
        "--bookings",
        type=Path,
        default=None,
        help=(
            f"Path to bookings.json "
            f"(default: {bookings_json_path().relative_to(project_root())})."
        ),
    )
    args = parser.parse_args()

    maybe_run_fetch(args)

    bookings_path = args.bookings or bookings_json_path()
    if not bookings_path.is_file():
        print(
            f"Missing {bookings_path}. Run without --no-fetch or run ./fetch.sh.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.diff_checkouts:
        payload = json.loads(bookings_path.read_text(encoding="utf-8"))
        print_checkouts_diff_from_payload(
            payload,
            section_header=DIFF_SECTION_HEADER,
        )
        write_checkouts_text(
            bookings_path=bookings_path,
            section_header=SUMMARY_SECTION_HEADER,
        )
    else:
        write_checkouts_text(bookings_path=bookings_path)


if __name__ == "__main__":
    main()
