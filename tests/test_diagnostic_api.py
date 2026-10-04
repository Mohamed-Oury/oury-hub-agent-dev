"""Tests d'intégration de l'API de diagnostic monétique."""

from fastapi.testclient import TestClient
from agentic.api.main import app

client = TestClient(app)


def test_diagnostic_analyze_endpoint_success() -> None:
    payload = {
        "title": "GAB — Retraits rejetés suite à saturation pool de connexion",
        "domain": "GAB",
        "severity": "HIGH",
        "symptom": "Le client insère sa carte, saisit son PIN mais l'automate affiche « Opération impossible — délais dépassé ».",
        "facts": "85 retraits refusés en 20 minutes sur les automates NCR du secteur NORD.",
        "stan": "739214",
        "errorCode": "DE39=00",
        "scope": "Automates GAB secteur NORD",
    }

    response = client.post("/api/v1/diagnostic/analyze", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    # Vérification des sections principales du DiagnosticResult
    assert "initialAnalysis" in data
    assert data["initialAnalysis"]["detectedDomain"] == "GAB"
    assert data["initialAnalysis"]["confidenceScore"] >= 70

    assert "flowMapping" in data
    assert len(data["flowMapping"]) >= 4

    assert "timeline" in data
    assert len(data["timeline"]) >= 3

    assert "hypotheses" in data
    assert len(data["hypotheses"]) >= 2
    # Vérification que H4 (Cash dispenser) est présente avec une probabilité élevée
    h4 = next((h for h in data["hypotheses"] if h["id"] == "H4"), None)
    assert h4 is not None
    assert h4["probaPercent"] >= 50

    assert "similarIncidents" in data
    assert len(data["similarIncidents"]) >= 1

    assert "evidenceList" in data
    assert len(data["evidenceList"]) >= 1

    assert "rcaProposal" in data
    # Validation du Garde-fou humain
    assert data["rcaProposal"]["status"] == "PROPOSED_UNCONFIRMED"
    assert data["rcaProposal"]["humanValidationRequired"] is True


def test_diagnostic_analyze_endpoint_invalid_payload() -> None:
    payload = {
        "title": "A",  # Trop court (min 2 chars)
        "symptom": "",  # Erreur requise
    }
    response = client.post("/api/v1/diagnostic/analyze", json=payload)
    assert response.status_code == 422
