"""Tests d'intégration de l'API d'Audit Trail unifié et du contrôle RBAC."""

from fastapi.testclient import TestClient
from agentic.api.main import app

client = TestClient(app)


def test_audit_record_and_trail() -> None:
    ticket_id = "INC-TEST-001"
    payload = {
        "ticketId": ticket_id,
        "stan": "739214",
        "domain": "GAB",
        "actionType": "DIAGNOSTIC",
        "operatorId": "op-monetique-01",
        "role": "MONETIQUE_OPERATOR",
        "evidenceSummary": ["Trame 0200 reçue", "Host timeout 25s", "DE39=91 constaté"],
        "status": "SUCCESS",
        "details": {"amount": "50000 XOF", "device": "ATM00452"},
    }

    # 1. Enregistrement d'un audit
    response = client.post("/api/v1/audit/record", json=payload)
    assert response.status_code == 200, response.text
    record = response.json()
    assert record["ticketId"] == ticket_id
    assert record["stan"] == "739214"
    assert record["actionType"] == "DIAGNOSTIC"

    # 2. Consultation de l'audit par ticket_id
    response_trail = client.get(f"/api/v1/audit/trail/{ticket_id}")
    assert response_trail.status_code == 200, response_trail.text
    trail = response_trail.json()
    assert len(trail) >= 1
    assert any(rec["ticketId"] == ticket_id for rec in trail)


def test_audit_rbac_permission_denied() -> None:
    # Un développeur CBS ne peut pas forcer une opération monétique sans rôle MONETIQUE_OPERATOR
    payload = {
        "ticketId": "INC-TEST-002",
        "domain": "GAB",
        "actionType": "DIAGNOSTIC",
        "operatorId": "dev-cbs-01",
        "role": "CBS_DEVELOPER",  # Rôle non habilité pour le diagnostic monétique
        "evidenceSummary": [],
        "status": "PENDING",
        "details": {},
    }

    response = client.post("/api/v1/audit/record", json=payload)
    assert response.status_code == 403
    assert "non autorisée" in response.json()["detail"]
