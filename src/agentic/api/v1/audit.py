"""Routes API REST pour l'observabilité et l'Audit Trail unifié."""

from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from agentic.schemas.audit import AuditActionType, AuditRecord, AuditRole
from agentic.services.audit_trail import UnifiedAuditService

router = APIRouter(prefix="/api/v1/audit", tags=["audit-observabilité"])


class RecordEventRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    ticket_id: str = Field(description="Numéro de ticket support ou identifiant incident.")
    domain: str = Field(description="Domaine concerné (GAB, SWITCH, CBS, HSM).")
    action_type: AuditActionType = Field(description="Type d'opération.")
    stan: str | None = Field(default=None, description="STAN de la transaction.")
    operator_id: str = Field(default="operator-01", description="Identifiant opérateur.")
    role: AuditRole = Field(default=AuditRole.MONETIQUE_OPERATOR, description="Rôle RBAC.")
    evidence_summary: list[str] = Field(default_factory=list, description="Preuves matérielles constatées.")
    status: str = Field(default="SUCCESS", description="Statut de l'action.")
    details: dict[str, Any] = Field(default_factory=dict, description="Métadonnées d'audit.")


@router.post("/record", response_model=AuditRecord, summary="Enregistrer un événement auditable")
def record_event(req: RecordEventRequest) -> AuditRecord:
    # Contrôle de permission RBAC
    if not UnifiedAuditService.check_permission(req.role, req.action_type):
        raise HTTPException(
            status_code=403,
            detail=f"Action '{req.action_type}' non autorisée pour le rôle RBAC '{req.role}'.",
        )

    return UnifiedAuditService.record_event(
        ticket_id=req.ticket_id,
        domain=req.domain,
        action_type=req.action_type,
        stan=req.stan,
        operator_id=req.operator_id,
        role=req.role,
        evidence_summary=req.evidence_summary,
        status=req.status,
        details=req.details,
    )


@router.get("/trail", response_model=list[AuditRecord], summary="Lister les enregistrements d'audit")
def get_trail(
    ticket_id: str | None = Query(default=None, description="Filtrer par ticket ID"),
    domain: str | None = Query(default=None, description="Filtrer par domaine"),
) -> list[AuditRecord]:
    return UnifiedAuditService.get_trail(ticket_id=ticket_id, domain=domain)


@router.get("/trail/{ticket_id}", response_model=list[AuditRecord], summary="Historique complet d'un ticket")
def get_trail_by_ticket(ticket_id: str) -> list[AuditRecord]:
    records = UnifiedAuditService.get_trail(ticket_id=ticket_id)
    if not records:
        raise HTTPException(status_code=404, detail=f"Aucun audit trouvé pour le ticket '{ticket_id}'.")
    return records
