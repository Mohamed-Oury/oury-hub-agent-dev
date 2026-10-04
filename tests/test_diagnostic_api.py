"""Tests d'intégration de l'API de diagnostic monétique (Grounding, Evidence Taxonomy & Missing Evidence)."""

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
    assert h4["confidenceLevel"] in ["ÉLEVÉE", "TRÈS ÉLEVÉE"]


def test_diagnostic_scenario_2_payway_host_timeout_grounding() -> None:
    """Test de l'Incident 2 : Payway -> Host TIMEOUT avec DE39=91 et typage E04 INFERENCE."""
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

    # 1. Point de rupture localisé sur Payway -> Host
    assert "Payway ➜ Host" in data["breakpointAnalysis"]

    # 2. Vérification des causes techniques possibles décomposées
    assert len(data["potentialTechnicalCauses"]) >= 3

    # 3. Vérification que H1 est l'hypothèse principale retenue avec niveau de confiance élevé
    h1 = next((h for h in data["hypotheses"] if h["id"] == "H1"), None)
    assert h1 is not None
    assert h1["status"] == "SUPPORTED"
    assert h1["confidenceLevel"] == "TRÈS ÉLEVÉE"
    assert h1["supportingEvidenceCount"] == 4
    assert h1["contradictingEvidenceCount"] == 0

    # 4. Vérification que H4 (Cash Dispenser) est REJETÉ avec 0 preuve d'appui
    h4 = next((h for h in data["hypotheses"] if h["id"] == "H4"), None)
    assert h4 is not None
    assert h4["status"] == "REJECTED"
    assert h4["supportingEvidenceCount"] == 0

    # 5. Vérification du typage exact de E04 dans l'Evidence Ledger : INFERENCE (et non HISTORICAL_REFERENCE)
    ledger = data["evidenceLedger"]
    e04 = next((item for item in ledger if item["id"] == "E04"), None)
    assert e04 is not None
    assert e04["type"] == "INFERENCE"
    assert e04["status"] == "HYPOTHESIS_INFERENCE"

    # 6. Vérification du tracker de preuves manquantes
    assert len(data["missingEvidence"]) >= 3
    assert "nextInvestigationStep" in data
