"""Tests d'intégration de l'API des Copilot Agents Décodeurs (EMV & ATM EJ)."""

from fastapi.testclient import TestClient
from agentic.api.main import app

client = TestClient(app)


def test_emv_decoder_agent_pin_error() -> None:
    payload = {
        "inputHex": "9F26084D5E12F9884511A29F2701809F10120110A00003220000000000000000000000009F3704C8912A349F3602005A95050000048000",
        "tvrRaw": "0000048000",
        "parsedTagsCount": 10,
        "criticalFlags": ["PIN Try Limit Exceeded"],
    }

    response = client.post("/api/v1/decoders/emv/analyze", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert "PIN" in data["summaryTitle"] or "Essais" in data["summaryTitle"]
    assert data["riskLevel"] in ["ÉLEVÉ", "CRITIQUE", "MOYEN"]
    assert len(data["recommendedActions"]) >= 2
    assert "tvrAnalysisDetail" in data


def test_atm_ej_decoder_agent_jam() -> None:
    payload = {
        "rawLog": "14:32:01 ATM: GAB-01\n14:32:14 HARDWARE ERROR: STACKER JAMMED IN TRANSPORT\n14:32:15 SHUTTER NOT OPENED",
        "vendor": "NCR",
        "atmId": "GAB-01",
        "claimAdvice": "FAVORABLE_RECREDIT",
    }

    response = client.post("/api/v1/decoders/atm-ej/analyze", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["hardwareFaultDetected"] is True
    assert "Bourrage" in data["summaryTitle"] or "Échec" in data["summaryTitle"]
    assert "FAVORABLE" in data["claimVerdictExplanation"]
    assert len(data["forensicChronology"]) >= 3
