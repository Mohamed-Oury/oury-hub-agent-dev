"""Tests unitaires du module de sécurité bancaire et conformité PCI-DSS."""

from agentic.core.security import PciDssSanitizer


def test_mask_pan_iso_de2() -> None:
    raw_text = "Transaction MTI=0200 DE2=4111223344556677 DE3=010000 DE4=000001000000"
    sanitized = PciDssSanitizer.mask_pan(raw_text)

    # Le PAN complet ne doit plus apparaître
    assert "4111223344556677" not in sanitized
    # Les 6 premiers chiffres et les 4 derniers doivent être préservés
    assert "4111 22** **** 6677" in sanitized or "411122******6677" in sanitized


def test_scrub_sensitive_pin_and_cvv() -> None:
    raw_text = "Message ISO 8583 : DE52=123456789ABCDEF0 CVV=123"
    scrubbed = PciDssSanitizer.scrub_sensitive_iso_fields(raw_text)

    assert "123456789ABCDEF0" not in scrubbed
    assert "[PIN_BLOCK_REDACTED_PCI_DSS]" in scrubbed
    assert "[REDACTED]" in scrubbed


def test_sanitize_payload_recursive() -> None:
    payload = {
        "title": "Incident GAB 0200",
        "logs": "Trace ISO: DE2=5412345678901234 DE52=AABBCCDDEEFF0011",
        "nested": {
            "cardNumber": "4970101234567890",
            "cvv": "CVV2: 987",
        },
        "count": 42,
    }

    sanitized = PciDssSanitizer.sanitize_payload(payload)

    assert "5412345678901234" not in str(sanitized)
    assert "AABBCCDDEEFF0011" not in str(sanitized)
    assert "4970101234567890" not in str(sanitized)
    assert sanitized["count"] == 42
