"""Chrome persistent profile + launch flags to minimize Chrome UI interruptions."""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import date
from pathlib import Path

from playwright.sync_api import BrowserContext, Playwright, sync_playwright

from fetch.airbnb_actions import (
    accept_airbnb_cookies_if_present,
    login_airbnb_if_needed,
)
from fetch.bookings_extract import (
    MONTHS_AHEAD,
    extract_bookings_if_multicalendar,
)
from shared.paths import project_root

PROFILE_NAME = "calendar-airbnb"
CDP_PORT = 9223  # remote debugging port to reuse an already-open Chrome instance

# Popups / annoyances we try to suppress:
# - default browser prompt
# - first-run / crash bubbles
# - translate UI / offers
# - password save bubble (also reinforced via Preferences — see below)
_CHROME_EXTRA_ARGS: tuple[str, ...] = (
    "--no-default-browser-check",
    "--no-first-run",
    "--disable-infobars",
    "--disable-session-crashed-bubble",
    "--disable-features=Translate,OfferTranslateEnabled",
    "--disable-save-password-bubble",
    f"--remote-debugging-port={CDP_PORT}",
)


def profile_user_data_dir(root: Path | None = None) -> Path:
    base = root or project_root()
    return base / "profiles" / PROFILE_NAME


def _merge_password_prefs(prefs_path: Path) -> None:
    """Best-effort prefs so Chrome stops nagging about saving passwords."""
    prefs_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if prefs_path.exists():
        try:
            raw = prefs_path.read_text(encoding="utf-8")
            if raw.strip():
                data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}

    profile = data.setdefault("profile", {})
    profile["password_manager_enabled"] = False
    data["credentials_enable_service"] = False
    data["credentials_enable_autosignin"] = False

    prefs_path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")



def _close_existing_cdp_browser(playwright: Playwright) -> None:
    """Close a leftover calendar-airbnb Chrome instance exposed on the CDP port."""
    try:
        browser = playwright.chromium.connect_over_cdp(
            f"http://localhost:{CDP_PORT}", timeout=2_000
        )
        browser.close()
    except Exception:
        pass

    subprocess.run(
        ["pkill", "-f", f"profiles/{PROFILE_NAME}"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.5)


def _is_airbnb_url(url: str) -> bool:
    return "airbnb.pt" in url or "airbnb.com" in url


def _shutdown_context(context: BrowserContext) -> None:
    """Close pages and the browser context as quickly as possible."""
    for page in list(context.pages):
        try:
            page.close(run_before_unload=False)
        except Exception:
            pass
    context.close()


def launch_chrome_profile(
    playwright: Playwright,
    *,
    root: Path | None = None,
    headless: bool = True,
    start_url: str | None = None,
    months_ahead: int = MONTHS_AHEAD,
    from_month: date | None = None,
    calendar_year: int | None = None,
) -> None:
    """
    Launch Google Chrome with a dedicated persistent profile directory.

    Profile path: <repo>/profiles/calendar-airbnb
    Override with env AIRBNB_CHROME_USER_DATA_DIR if you need another folder.
    """
    url = (start_url or os.environ.get("AIRBNB_START_URL") or "about:blank").strip()

    _close_existing_cdp_browser(playwright)

    explicit = os.environ.get("AIRBNB_CHROME_USER_DATA_DIR", "").strip()
    user_data_dir = Path(explicit) if explicit else profile_user_data_dir(root)
    default_prefs = user_data_dir / "Default" / "Preferences"
    _merge_password_prefs(default_prefs)

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        channel="chrome",
        headless=headless,
        args=list(_CHROME_EXTRA_ARGS),
        viewport={"width": 1280, "height": 800},
        locale="pt-PT",
        ignore_default_args=["--enable-automation"],
    )

    try:
        if url and url != "about:blank":
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(1500)
            if _is_airbnb_url(url):
                accept_airbnb_cookies_if_present(page)
                login_airbnb_if_needed(page, root=root)
                if "multicalendar" in url:
                    extract_bookings_if_multicalendar(
                        page,
                        root=root,
                        months_ahead=months_ahead,
                        from_month=from_month,
                        calendar_year=calendar_year,
                    )
    finally:
        _shutdown_context(context)


def open_profile_until_exit(
    *,
    root: Path | None = None,
    headless: bool = True,
    start_url: str | None = None,
    months_ahead: int = MONTHS_AHEAD,
    from_month: date | None = None,
    calendar_year: int | None = None,
) -> None:
    """Open Chrome, run the flow, and close when finished."""
    with sync_playwright() as p:
        launch_chrome_profile(
            p,
            root=root,
            headless=headless,
            start_url=start_url,
            months_ahead=months_ahead,
            from_month=from_month,
            calendar_year=calendar_year,
        )
