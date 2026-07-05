"""Tests for Web Push delivery helpers."""

from __future__ import annotations

from py_vapid import Vapid02

from notifications.push import load_vapid_private_key


class TestLoadVapidPrivateKey:
    def test_parses_pem_text_from_secret(self) -> None:
        vapid = Vapid02()
        vapid.generate_keys()
        pem = vapid.private_pem().decode("utf-8")
        loaded = load_vapid_private_key(pem)
        assert isinstance(loaded, Vapid02)

    def test_parses_single_line_pem(self) -> None:
        vapid = Vapid02()
        vapid.generate_keys()
        pem = vapid.private_pem().decode("utf-8")
        single_line = pem.replace("\n", " ").replace("  ", " ")
        loaded = load_vapid_private_key(single_line)
        assert isinstance(loaded, Vapid02)

    def test_passes_through_base64_der_string(self) -> None:
        value = "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg"
        assert load_vapid_private_key(value) == value
