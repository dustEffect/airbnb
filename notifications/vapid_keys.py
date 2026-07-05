#!/usr/bin/env python3
"""Generate a VAPID key pair for Web Push."""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid02


def _public_key_base64url(vapid: Vapid02) -> str:
    raw = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def main() -> None:
    vapid = Vapid02()
    vapid.generate_keys()
    public_key = _public_key_base64url(vapid)
    private_key = vapid.private_pem().decode("utf-8")

    print("Add these to GitHub Actions secrets:\n")
    print(f"VAPID_PUBLIC_KEY={public_key}")
    print(f"VAPID_PRIVATE_KEY={private_key}")
    print("\nAlso set VAPID_SUBJECT=mailto:your@email.com")
    print(
        "\nEmbed VAPID_PUBLIC_KEY when building the calendar "
        "(publish workflow already passes it)."
    )


if __name__ == "__main__":
    main()
