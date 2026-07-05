"""Send Web Push notifications to subscribed devices."""

from __future__ import annotations

import json
import os
from typing import Any

from py_vapid import Vapid02 as Vapid
from pywebpush import WebPushException, webpush


def normalize_vapid_subject(raw: str) -> str:
    """Return a mailto: subject accepted by py_vapid."""
    subject = raw.strip()
    if not subject:
        raise ValueError("Missing VAPID_SUBJECT (e.g. mailto:you@example.com).")
    if subject.startswith("mailto:"):
        return subject
    if "@" in subject and "://" not in subject:
        return f"mailto:{subject}"
    raise ValueError(
        f"Invalid VAPID_SUBJECT {subject!r}; use mailto:you@example.com or you@example.com"
    )


def vapid_claims_from_env() -> dict[str, str]:
    return {"sub": normalize_vapid_subject(os.environ.get("VAPID_SUBJECT", ""))}


def load_vapid_private_key(raw: str) -> str | Vapid:
    """Accept PEM text, a PEM file path, or a base64 DER string."""
    text = raw.strip().replace("\\n", "\n")
    if os.path.isfile(text):
        return text
    if "-----BEGIN" in text:
        if "\n" not in text:
            text = (
                text.replace("-----BEGIN PRIVATE KEY----- ", "-----BEGIN PRIVATE KEY-----\n")
                .replace(" -----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----")
            )
        return Vapid.from_pem(text.encode("utf-8"))
    return text


def send_push_notification(
    subscription: dict[str, Any],
    message: dict[str, str],
    *,
    vapid_private_key: str,
    vapid_claims: dict[str, str],
) -> None:
    webpush(
        subscription_info=subscription,
        data=json.dumps(message, ensure_ascii=False),
        vapid_private_key=load_vapid_private_key(vapid_private_key),
        vapid_claims=vapid_claims,
    )


def send_push_notifications(
    subscriptions: list[dict[str, Any]],
    message: dict[str, str],
    *,
    vapid_private_key: str,
    vapid_claims: dict[str, str],
) -> list[str]:
    """Send to each subscription. Returns human-readable errors (empty if all ok)."""
    errors: list[str] = []
    for index, subscription in enumerate(subscriptions, start=1):
        try:
            send_push_notification(
                subscription,
                message,
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims,
            )
        except WebPushException as exc:
            errors.append(f"subscription {index}: {exc}")
    return errors
