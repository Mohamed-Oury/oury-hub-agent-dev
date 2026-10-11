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


def test_diagnostic_scenario_incident_08_cash_dispenser_reversal() -> None:
    """Test complet de l'Incident 08 : Retrait GAB avec autorisation accordée (DE39=00),

    échec physique Cash Dispenser, Reversal 0420 NOT RECEIVED, et garde-fou régularisation.
    """
    payload = {
        "title": "GAB — Client débité malgré retrait non distribué",
        "domain": "GAB / Reversal",
        "severity": "HIGH",
        "symptom": "Le client demande 100 000 XOF. L'ATM ne distribue aucun billet. Le compte est pourtant débité.",
        "facts": "0200 → Host, 0210 DE39=00, ATM → problème physique, 0200/0420 reversal attendu, 0420 reversal : NOT RECEIVED",
        "errorCode": "DE39=00",
        "scope": "ATM00452",
    }

    response = client.post("/api/v1/diagnostic/analyze", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()

    # 1. Localisation : Détection du domaine et rupture Cash Dispenser & Reversal
    assert "GAB" in data["initialAnalysis"]["detectedDomain"]
    assert "Cash Dispenser" in data["breakpointAnalysis"]
    assert "Reversal" in data["breakpointAnalysis"]

    # 2. Cartographie du flux incluant le saut Reversal et le statut comptable
    reversal_hop = next((hop for hop in data["flowMapping"] if "Reversal" in hop["component"]), None)
    assert reversal_hop is not None
    assert reversal_hop["status"] == "ERROR"
    assert reversal_hop["mti"] == "0420"

    cbs_hop = next((hop for hop in data["flowMapping"] if "Core Banking" in hop["component"] and hop["status"] == "PENDING"), None)
    assert cbs_hop is not None

    # 3. Timeline avec anomalie critique Reversal
    reversal_event = next((evt for evt in data["timeline"] if evt["mti"] == "0420"), None)
    assert reversal_event is not None
    assert reversal_event["status"] == "REVERSAL_NOT_RECEIVED"

    # 4. Décomposition des causes techniques avec preuves associées
    assert len(data["potentialTechnicalCauses"]) >= 4
    assert any("Presenter Sensor" in cause for cause in data["potentialTechnicalCauses"])
    assert any("cassette" in cause.lower() for cause in data["potentialTechnicalCauses"])
    assert any("Timeout" in cause for cause in data["potentialTechnicalCauses"])
    assert any("Reversal" in cause for cause in data["potentialTechnicalCauses"])

    # 5. Hypothèses : H4 (Cash Dispenser) et H5 (Reversal) SUPPORTED, H1 REJECTED
    h4 = next((h for h in data["hypotheses"] if h["id"] == "H4"), None)
    assert h4 is not None
    assert h4["status"] == "SUPPORTED"
    assert h4["confidenceLevel"] in ["ÉLEVÉE", "TRÈS ÉLEVÉE"]

    h5 = next((h for h in data["hypotheses"] if h["id"] == "H5"), None)
    assert h5 is not None
    assert h5["status"] == "SUPPORTED"
    assert h5["confidenceLevel"] == "TRÈS ÉLEVÉE"

    h1 = next((h for h in data["hypotheses"] if h["id"] == "H1"), None)
    assert h1 is not None
    assert h1["status"] == "REJECTED"

    # 6. Registre de preuves normalisé (Evidence Ledger)
    ledger = data["evidenceLedger"]
    e01 = next((it for it in ledger if it["id"] == "E01"), None)
    assert e01 is not None and e01["type"] == "VERIFIED_EVIDENCE"  # DE39=00
    assert e01["status"] == "VALIDATED_FACT"

    e02 = next((it for it in ledger if it["id"] == "E02"), None)
    assert e02 is not None and e02["type"] == "VERIFIED_EVIDENCE"  # Non-distribution physique
    assert e02["status"] == "VALIDATED_FACT"

    e03 = next((it for it in ledger if it["id"] == "E03"), None)
    assert e03 is not None and e03["type"] == "VERIFIED_EVIDENCE"  # Reversal 0420 NOT RECEIVED
    assert e03["status"] == "VALIDATED_FACT"

    e04 = next((it for it in ledger if it["id"] == "E04"), None)
    assert e04 is not None and e04["type"] == "INFERENCE"  # Défaillance Cash Dispenser
    assert e04["status"] == "HYPOTHESIS_INFERENCE"

    e05 = next((it for it in ledger if it["id"] == "E05"), None)
    assert e05 is not None and e05["type"] == "INFERENCE"  # Risque débit financier client
    assert e05["status"] == "HYPOTHESIS_INFERENCE"

    e07 = next((it for it in ledger if it["id"] == "E07"), None)
    assert e07 is not None and e07["type"] == "REJECTED_CONTRADICTION"  # DE39=91 éliminé

    # 7. Checklist des preuves manquantes (Missing Evidence)
    assert len(data["missingEvidence"]) >= 4
    assert any("Electronic Journal" in item for item in data["missingEvidence"])
    assert any("Cash Dispenser" in item for item in data["missingEvidence"])
    assert any("Reversal" in item for item in data["missingEvidence"])
    assert any("Core Banking" in item or "comptable" in item.lower() for item in data["missingEvidence"])

    # 8. RCA Proposal & Garde-fou humain
    rca = data["rcaProposal"]
    assert rca["status"] == "PROPOSED_UNCONFIRMED"
    assert rca["humanValidationRequired"] is True
    assert "NON CONFIRMÉE" in rca["summary"]
    assert "AUCUNE RÉGULARISATION COMPTABLE" in rca["summary"]

    # 9. Runbooks incluant audit Reversal et régularisation sécurisée
    assert any("RB-MON-001" in act for act in rca["recommendedActions"])
    assert any("RB-MON-025" in act for act in rca["recommendedActions"])
    assert any("RB-MON-099" in act for act in rca["recommendedActions"])

