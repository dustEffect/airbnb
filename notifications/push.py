"""Send Web Push notifications to subscribed devices."""

from __future__ import annotations

import json
from typing import Any

from pywebpush import WebPushException, webpush


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
        vapid_private_key=vapid_private_key,
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
