"""Actions on the Airbnb web UI (cookie banner, login, etc.)."""

from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from airbnb_calendar.env_loader import get_airbnb_credentials, load_credentials_env


def accept_airbnb_cookies_if_present(page: Page, *, click_timeout_ms: int = 4500) -> None:
    """
    If the cookie banner appears (e.g. "Accept all" button), click and dismiss it.

    Does not fail if the banner was already accepted or is absent in this session.
    """
    rx = re.compile(r"^\s*(Aceitar tudo|Accept all)\s*$", re.I)
    btn = page.get_by_role("button", name=rx)
    try:
        btn.first.click(timeout=click_timeout_ms)
        return
    except PlaywrightTimeoutError:
        pass

    # Sometimes the label is on a clickable element that is not role=button
    for label in ("Aceitar tudo", "Accept all"):
        linkish = page.get_by_text(label, exact=True)
        try:
            linkish.first.click(timeout=1800)
            return
        except PlaywrightTimeoutError:
            continue


_CONTINUE_EMAIL = re.compile(
    r"Continuar com (?:o )?e?-?mail|Continue with email",
    re.I,
)

# "Welcome back" modal with email + password fields visible at once (PT UI)
_WELCOME_BACK = re.compile(
    r"Damos-lhe novamente as boas[\s-]*vindas",
    re.I,
)

_EMAIL_NAME = re.compile(r"^E-mail$", re.I)
_PASSWORD_NAME = re.compile(r"^Palavra-passe$", re.I)
_PHONE_OR_EMAIL = re.compile(
    r"Número de telefone ou e-mail|Phone number or email",
    re.I,
)
_CONTINUE = re.compile(r"^Continuar$|^Continue$", re.I)
_LOGIN = re.compile(r"^Entrar$|^Log in$", re.I)


def _airbnb_email_locator(page: Page):
    """Prefer stable selectors; multicalendar login uses #phone-or-email."""
    return (
        page.locator("#phone-or-email")
        .or_(page.get_by_test_id("email-login-email"))
        .or_(page.get_by_test_id("login-signup-email"))
        .or_(page.get_by_role("textbox", name=_EMAIL_NAME))
        .or_(page.get_by_placeholder(_PHONE_OR_EMAIL))
    )


def _airbnb_password_locator(page: Page):
    return (
        page.get_by_test_id("email-signup-password")
        .or_(page.get_by_test_id("login-signup-password"))
        .or_(page.get_by_test_id("login-password"))
        .or_(page.get_by_role("textbox", name=_PASSWORD_NAME))
    )


def _continue_submit_button(page: Page):
    """Primary submit button — exact match to avoid Google/Apple social buttons."""
    return page.get_by_role("button", name=_CONTINUE)


def _login_submit_button(page: Page):
    return page.get_by_role("button", name=_LOGIN)


def _submit_password_if_present(page: Page, password: str, *, timeout_ms: int = 4000) -> None:
    """Fill password and log in when the field appears; otherwise leave manual steps to the user."""
    pwd = _airbnb_password_locator(page).first
    try:
        pwd.wait_for(state="visible", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        return
    pwd.fill(password)
    _login_submit_button(page).click()


def _try_login_welcome_back_modal(page: Page, root: Path | None) -> bool:
    """
    Alternate flow: welcome-back modal with both fields visible → fill and submit.
    Returns True if this flow was executed.
    """
    marker = page.get_by_text(_WELCOME_BACK).first
    try:
        if not marker.is_visible(timeout=2000):
            return False
    except PlaywrightTimeoutError:
        return False

    load_credentials_env(root)
    email, password = get_airbnb_credentials()

    _airbnb_email_locator(page).fill(email)
    _airbnb_password_locator(page).fill(password)
    _login_submit_button(page).click()
    return True


def _try_login_direct_identifier_flow(page: Page, root: Path | None) -> bool:
    """
    Login page with phone/email field already visible (e.g. /login?redirect_url=/multicalendar).
    Returns True if this flow was executed.
    """
    identifier = _airbnb_email_locator(page).first
    try:
        if not identifier.is_visible(timeout=2000):
            return False
    except PlaywrightTimeoutError:
        return False

    pwd = _airbnb_password_locator(page).first
    try:
        if pwd.is_visible(timeout=500):
            return False
    except PlaywrightTimeoutError:
        pass

    load_credentials_env(root)
    email, password = get_airbnb_credentials()

    identifier.fill(email)
    _continue_submit_button(page).click()
    _submit_password_if_present(page, password)
    return True


def _try_login_continue_with_email_flow(page: Page, root: Path | None) -> bool:
    """
    Social-auth picker: Continue with email → email → Continue → password → Log in.
    Returns True if this flow was executed.
    """
    continue_email = page.get_by_test_id("social-auth-button-email").or_(
        page.get_by_role("button", name=_CONTINUE_EMAIL)
    )
    try:
        continue_email.first.click(timeout=5500)
    except PlaywrightTimeoutError:
        return False

    load_credentials_env(root)
    email, password = get_airbnb_credentials()

    _airbnb_email_locator(page).fill(email)
    _continue_submit_button(page).click()
    _submit_password_if_present(page, password)
    return True


def login_airbnb_if_needed(page: Page, *, root: Path | None = None) -> None:
    """
    If not authenticated:

    1. Welcome-back modal (email + password visible): fill and submit.
    2. Direct phone/email field (multicalendar login redirect): fill → Continue, then password if shown.
    3. Social-auth picker: Continue with email → email → Continue, then password if shown.

    Steps after Continue (e.g. SMS verification) are manual and not handled here.

    Credentials: AIRBNB_EMAIL / AIRBNB_PASSWORD in credentials.local.env.

    If already logged in (none of these UI elements appear), returns without error.
    """
    if _try_login_welcome_back_modal(page, root):
        return
    if _try_login_direct_identifier_flow(page, root):
        return
    _try_login_continue_with_email_flow(page, root)
