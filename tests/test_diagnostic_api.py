"""Tests d'intégration de l'API de diagnostic monétique (Grounding & Contradictions)."""

from fastapi.testclient import TestClient
from agentic.api.main import app

client = TestClient(app)


def test_diagnostic_scenario_1_cash_dispenser() -> None:
    payload = {
        "title": "GAB — Retrait 50 000 XOF en timeout post-autorisation",
        "domain": "GAB",
        "severity": "HIGH",
        "symptom": "Le client insère sa carte, saisit son PIN mais l'automate affiche Opération impossible — délais dépassé. Le compte semble avoir été débité.",
        "facts": "Compte débité de 50 000 XOF avec retour DE39=00",
        "stan": "739214",
        "errorCode": "DE39=00",
        "scope": "ATM00452",
    }

    response = client.post("/api/v1/diagnostic/analyze", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["initialAnalysis"]["detectedDomain"] == "GAB"
    assert "Cash Dispenser" in data["breakpointAnalysis"]

    h4 = next((h for h in data["hypotheses"] if h["id"] == "H4"), None)
    assert h4 is not None
    assert h4["status"] == "SUPPORTED"
    assert h4["probaPercent"] >= 70


def test_diagnostic_scenario_2_payway_host_timeout_grounding() -> None:
    """Test de l'Incident 2 : Payway -> Host TIMEOUT avec DE39=91."""
    payload = {
        "title": "GAB — Rejets massifs après timeout Payway vers Host",
        "domain": "GAB",
        "severity": "CRITICAL",
        "symptom": "Depuis 10h15, les retraits GAB sont majoritairement rejetés avec un délai dépassé. Payway reçoit correctement les demandes ATM mais les réponses du Host arrivent très tardivement ou ne sont pas reçues.",
        "facts": "Payway -> Host TIMEOUT. 86% des transactions en DE39=91. Host aucune réponse.",
        "stan": "109823",
        "errorCode": "DE39=91",
        "scope": "Switch Payway ➜ Host",
    }

    response = client.post("/api/v1/diagnostic/analyze", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    # 1. Vérification du point de rupture localisé sur Payway -> Host
    assert "Payway ➜ Host" in data["breakpointAnalysis"]

    # 2. Vérification que H1 (Host Inoperative) est l'hypothèse principale retenue à 86%
    h1 = next((h for h in data["hypotheses"] if h["id"] == "H1"), None)
    assert h1 is not None
    assert h1["status"] == "SUPPORTED"
    assert h1["probaPercent"] == 86

    # 3. Vérification que H4 (Cash Dispenser) est REJETÉ avec 0% (Pas de contamination de contexte)
    h4 = next((h for h in data["hypotheses"] if h["id"] == "H4"), None)
    assert h4 is not None
    assert h4["status"] == "REJECTED"
    assert h4["probaPercent"] == 0

    # 4. Vérification de la présence du filtre de contradiction
    assert len(data["contradictionsDetected"]) >= 1
    assert any("DE39=00" in c for c in data["contradictionsDetected"])

    # 5. Vérification du registre des preuves (Evidence Ledger)
    assert "evidenceLedger" in data
    assert len(data["evidenceLedger"]) >= 4
    rejected_ledger = [item for item in data["evidenceLedger"] if item["type"] == "REJECTED_CONTRADICTION"]
    assert len(rejected_ledger) >= 1
