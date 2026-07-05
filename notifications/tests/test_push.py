"""Tests for Web Push delivery helpers."""

from __future__ import annotations

from py_vapid import Vapid02

from notifications.push import load_vapid_private_key, normalize_vapid_subject, vapid_claims_from_env


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


class TestNormalizeVapidSubject:
    def test_accepts_mailto_prefix(self) -> None:
        assert normalize_vapid_subject("mailto:host@example.com") == "mailto:host@example.com"

    def test_adds_mailto_to_bare_email(self) -> None:
        assert normalize_vapid_subject("host@example.com") == "mailto:host@example.com"

    def test_rejects_empty(self) -> None:
        try:
            normalize_vapid_subject("   ")
            raise AssertionError("expected ValueError")
        except ValueError as exc:
            assert "Missing VAPID_SUBJECT" in str(exc)

