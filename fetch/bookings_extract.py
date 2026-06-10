"""Extract multicalendar bookings via Airbnb GraphQL APIs and write bookings.json."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import APIRequestContext, Page, TimeoutError as PlaywrightTimeoutError

from shared.paths import bookings_json_path

from airbnb_urls import multicalendar_url
MONTHS_AHEAD = 3
LISTINGS_PAGE_SIZE = 6

# Persisted GraphQL operation hashes (from multicalendar network traffic).
_MULTICAL_LISTINGS_HASH = "a92f15db8f3b41bec137649a08df84ad0129c7d6f45a96606bd0d779811f33f4"
_ADDITIONAL_RESERVATION_HASH = "7c89708c64fa1ca8288dc79c3627d97088cf872ceb542b883eb9dafec7dfee2d"

_CALENDAR_FIELDS = [
    "AVAILABILITY",
    "AVAILABILITY_DETAILS",
    "REASONS_FOR_UNAVAILABILITY",
    "HOST_PRICE",
    "SMART_PRICING_SUGGESTIONS",
    "HOST_PRICE_EXPLANATIONS",
    "PROMOTION",
    "LUX_INSPECTIONS",
    "BOOKABILITY",
    "ANCHOR_PRICE",
]

_LISTING_FILTERS = {
    "amenityIds": None,
    "apiStatuses": None,
    "bathrooms": None,
    "beds": None,
    "bedrooms": None,
    "cities": None,
    "instantBook": None,
    "listingIds": None,
    "ownerships": None,
    "propertyTypeGroups": None,
    "propertyTypeIds": None,
    "publishedApiSyncCategories": None,
    "statuses": None,
    "tags": None,
    "pttAllowed": None,
    "updatedAfter": None,
    "updatedBefore": None,
    "visibilities": None,
    "vlsVerificationRequired": None,
    "tierIds": [0, 1, 2],
}

_AIRBNB_API_KEY = "d306zoyjsyarp7ifhu67rjxn52tv0t20"


def bookings_output_path(root: Path | None = None) -> Path:
    return bookings_json_path(root)


def parse_start_month(value: str) -> date:
    """Parse YYYY-MM into the first day of that month."""
    try:
        year_str, month_str = value.strip().split("-", 1)
        return date(int(year_str), int(month_str), 1)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid month {value!r}; use YYYY-MM (e.g. 2026-06).") from exc


def _print_processing_intro(start_date: str, end_date: str) -> None:
    print(
        f"Processing Airbnb multicalendar bookings from {start_date} to {end_date}.",
        flush=True,
    )
    print(flush=True)


def _date_range(
    months_ahead: int = MONTHS_AHEAD,
    *,
    from_month: date | None = None,
    calendar_year: int | None = None,
) -> tuple[str, str]:
    if calendar_year is not None:
        start = date(calendar_year, 1, 1)
        end = date(calendar_year, 12, 31)
        return start.isoformat(), end.isoformat()

    today = date.today()
    start = from_month or today
    end = start + timedelta(days=months_ahead * 31)
    return start.isoformat(), end.isoformat()


def _api_origin(page: Page) -> str:
    match = re.match(r"(https://[^/]+)", page.url)
    return match.group(1) if match else "https://www.airbnb.pt"


def _persisted_query_url(
    origin: str,
    *,
    operation_name: str,
    sha256_hash: str,
    variables: dict,
    locale: str = "pt-PT",
    currency: str = "EUR",
) -> str:
    params = {
        "operationName": operation_name,
        "locale": locale,
        "currency": currency,
        "variables": json.dumps(variables, separators=(",", ":")),
        "extensions": json.dumps(
            {"persistedQuery": {"version": 1, "sha256Hash": sha256_hash}},
            separators=(",", ":"),
        ),
    }
    return f"{origin}/api/v3/{operation_name}/{sha256_hash}?{urlencode(params)}"


def _api_headers(origin: str) -> dict[str, str]:
    return {
        "accept": "*/*",
        "content-type": "application/json",
        "x-airbnb-api-key": _AIRBNB_API_KEY,
        "x-airbnb-supports-airlock-v2": "true",
        "referer": f"{origin}/multicalendar",
    }


def _fetch_json(request: APIRequestContext, url: str, origin: str) -> dict:
    response = request.get(url, headers=_api_headers(origin))
    if not response.ok:
        raise RuntimeError(
            f"Airbnb API request failed ({response.status}): {url[:120]}…"
        )
    return response.json()


def _fetch_multical_listings_page(
    request: APIRequestContext,
    origin: str,
    *,
    start_date: str,
    end_date: str,
    offset: int,
) -> dict:
    variables = {
        "offset": offset,
        "limit": LISTINGS_PAGE_SIZE,
        "startDate": start_date,
        "endDate": end_date,
        "calendarFields": _CALENDAR_FIELDS,
        "filters": _LISTING_FILTERS,
    }
    url = _persisted_query_url(
        origin,
        operation_name="multicalListingsAndCalendars",
        sha256_hash=_MULTICAL_LISTINGS_HASH,
        variables=variables,
    )
    return _fetch_json(request, url, origin)


def _fetch_additional_reservation_data(
    request: APIRequestContext,
    origin: str,
    *,
    listing_ids: list[str],
    start_date: str,
    end_date: str,
) -> dict[str, dict]:
    if not listing_ids:
        return {}

    variables = {
        "listingIds": listing_ids,
        "startDate": start_date,
        "endDate": end_date,
    }
    url = _persisted_query_url(
        origin,
        operation_name="multicalAdditionalReservationData",
        sha256_hash=_ADDITIONAL_RESERVATION_HASH,
        variables=variables,
    )
    payload = _fetch_json(request, url, origin)
    resources = (
        payload.get("data", {})
        .get("patek", {})
        .get("getAdditionalReservationData", {})
        .get("reservationResources", [])
        or []
    )
    return {
        item["confirmationCode"]: item
        for item in resources
        if item.get("confirmationCode")
    }


def _listing_names_from_payload(payload: dict) -> dict[str, str]:
    listings = (
        payload.get("data", {})
        .get("patek", {})
        .get("getMultiCalendarListingsAndCalendars", {})
        .get("multiCalendarListingsAttributes", {})
        .get("multiCalendarListings", [])
        or []
    )
    names: dict[str, str] = {}
    for listing in listings:
        listing_id = listing.get("listingId")
        if not listing_id:
            continue
        names[str(listing_id)] = (
            listing.get("listingNameOrPlaceholderName")
            or listing.get("nickname")
            or str(listing_id)
        )
    return names


def _reservations_from_payload(
    payload: dict,
    listing_names: dict[str, str],
) -> dict[str, dict]:
    calendars = (
        payload.get("data", {})
        .get("patek", {})
        .get("getMultiCalendarListingsAndCalendars", {})
        .get("hostCalendarsResponse", {})
        .get("calendars", [])
        or []
    )

    reservations: dict[str, dict] = {}
    for calendar in calendars:
        listing_id = str(calendar.get("listingId") or "")
        listing_name = (
            (calendar.get("listingAttributes") or {}).get("listingName")
            or listing_names.get(listing_id)
            or listing_id
        )
        for day in calendar.get("days", []):
            reservation = ((day.get("unavailabilityReasons") or {}).get("reservation"))
            if not reservation:
                continue
            code = reservation.get("confirmationCode")
            if not code or code in reservations:
                continue

            guest = reservation.get("guestInfo") or {}
            reservations[code] = {
                "confirmationCode": code,
                "listingId": str(reservation.get("hostingId") or listing_id),
                "listingName": listing_name,
                "guestFirstName": guest.get("firstName"),
                "guestLastName": guest.get("lastName"),
                "startDate": reservation.get("startDate"),
                "endDate": reservation.get("endDate"),
                "nights": reservation.get("nights"),
                "basePrice": reservation.get("basePrice"),
                "currency": reservation.get("hostCurrency"),
                "numberOfGuests": reservation.get("numberOfGuests"),
                "numberOfAdults": reservation.get("numberOfAdults"),
                "numberOfChildren": reservation.get("numberOfChildren"),
                "numberOfInfants": reservation.get("numberOfInfants"),
                "status": reservation.get("statusString"),
            }
    return reservations


def _fetch_all_reservations(
    request: APIRequestContext,
    origin: str,
    *,
    start_date: str,
    end_date: str,
) -> tuple[dict[str, dict], list[str]]:
    reservations: dict[str, dict] = {}
    listing_names: dict[str, str] = {}
    listing_ids: list[str] = []
    offset = 0

    while True:
        payload = _fetch_multical_listings_page(
            request,
            origin,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
        )
        listing_names.update(_listing_names_from_payload(payload))
        reservations.update(
            _reservations_from_payload(payload, listing_names)
        )

        page_listings = (
            payload.get("data", {})
            .get("patek", {})
            .get("getMultiCalendarListingsAndCalendars", {})
            .get("multiCalendarListingsAttributes", {})
            .get("multiCalendarListings", [])
            or []
        )
        if not page_listings:
            break

        for listing in page_listings:
            listing_id = str(listing.get("listingId") or "")
            if listing_id and listing_id not in listing_ids:
                listing_ids.append(listing_id)

        record_count = (
            payload.get("data", {})
            .get("patek", {})
            .get("getMultiCalendarListingsAndCalendars", {})
            .get("multiCalendarListingsAttributes", {})
            .get("metadata", {})
            .get("recordCount", len(page_listings))
        )
        if record_count < LISTINGS_PAGE_SIZE:
            break
        offset += LISTINGS_PAGE_SIZE

    return reservations, listing_ids


def _wait_for_multicalendar(page: Page, *, timeout_ms: int = 300_000) -> bool:
    if "multicalendar" in page.url and "login" not in page.url:
        return True
    try:
        page.wait_for_url(re.compile(r".*/multicalendar(?:\?.*)?$"), timeout=timeout_ms)
        return True
    except PlaywrightTimeoutError:
        return False


def extract_bookings_if_multicalendar(
    page: Page,
    *,
    root: Path | None = None,
    months_ahead: int = MONTHS_AHEAD,
    from_month: date | None = None,
    calendar_year: int | None = None,
) -> Path | None:
    """
    Fetch bookings for the next `months_ahead` months and write bookings.json.
    Returns the output path, or None if not on multicalendar / fetch failed.
    """
    if multicalendar_url() not in page.url and "multicalendar" not in page.url:
        return None

    if not _wait_for_multicalendar(page):
        print("Skipping bookings extract: multicalendar did not load.", flush=True)
        return None

    start_date, end_date = _date_range(
        months_ahead,
        from_month=from_month,
        calendar_year=calendar_year,
    )
    _print_processing_intro(start_date, end_date)
    origin = _api_origin(page)
    request = page.context.request

    try:
        reservations, listing_ids = _fetch_all_reservations(
            request,
            origin,
            start_date=start_date,
            end_date=end_date,
        )
        extras = _fetch_additional_reservation_data(
            request,
            origin,
            listing_ids=listing_ids,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:
        print(f"Bookings extract failed: {exc}", flush=True)
        return None

    for code, extra in extras.items():
        booking = reservations.setdefault(
            code,
            {"confirmationCode": code},
        )
        booking["hostPayoutFormatted"] = extra.get("hostPayoutFormatted")
        booking["hostFacingStatus"] = extra.get("hostFacingStatus")

    bookings = sorted(
        reservations.values(),
        key=lambda b: (b.get("startDate") or "", b.get("confirmationCode") or ""),
    )

    output = {
        "extractedAt": date.today().isoformat(),
        "dateRange": {"startDate": start_date, "endDate": end_date},
        "bookingCount": len(bookings),
        "bookings": bookings,
    }

    out_path = bookings_output_path(root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_path
