"""Schémas pour l'Audit Trail unifié et le contrôle des permissions RBAC."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic.main import BaseModel


class AuditRole(str, Enum):
    """Rôles habilités dans le Monétique & CBS Hub."""

    MONETIQUE_OPERATOR = "MONETIQUE_OPERATOR"
    CBS_DEVELOPER = "CBS_DEVELOPER"
    SECURITY_ADMIN = "SECURITY_ADMIN"
    AUDITOR = "AUDITOR"


class AuditActionType(str, Enum):
    """Types d'opérations enregistrées dans l'Audit Trail."""

    DIAGNOSTIC = "DIAGNOSTIC"
    CODE_GENERATION = "CODE_GENERATION"
    OPERATOR_DECISION = "OPERATOR_DECISION"
    ANALYSIS = "ANALYSIS"
    SECURITY_SCRUB = "SECURITY_SCRUB"


class AuditRecord(BaseModel):
    """Enregistrement unifié corrélant tickets, transactions, preuves et décisions."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    record_id: str = Field(description="Identifiant unique de l'audit.")
    ticket_id: str = Field(description="Numéro de ticket support ou identifiant d'incident.")
    stan: str | None = Field(default=None, description="STAN de la transaction monétique le cas échéant.")
    domain: str = Field(description="Domaine concerné (GAB, SWITCH, CBS, HSM).")
    action_type: AuditActionType = Field(description="Nature de l'action exécutée.")
    operator_id: str = Field(default="system", description="Identifiant de l'agent ou de l'opérateur.")
    role: AuditRole = Field(default=AuditRole.MONETIQUE_OPERATOR, description="Rôle RBAC de l'exécutant.")
    evidence_summary: list[str] = Field(default_factory=list, description="Résumé des preuves matérielles constatées.")
    status: str = Field(default="SUCCESS", description="Statut de l'opération (SUCCESS, PENDING_APPROVAL, APPROVED).")
    details: dict[str, Any] = Field(default_factory=dict, description="Métadonnées complémentaires.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Horodatage UTC de l'événement.",
    )
