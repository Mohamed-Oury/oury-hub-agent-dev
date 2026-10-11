"""Service d'Audit Trail unifié et contrôle des permissions RBAC pour le Monétique & CBS Hub."""

import json
from pathlib import Path
import uuid
from typing import Any

from agentic.schemas.audit import AuditActionType, AuditRecord, AuditRole

AUDIT_DIR = Path("outputs/audit")
AUDIT_FILE = AUDIT_DIR / "audit_trail.jsonl"


class UnifiedAuditService:
    """Gestionnaire central de traçabilité, conformité et audit unifié."""

    _role_permissions: dict[AuditRole, set[AuditActionType]] = {
        AuditRole.MONETIQUE_OPERATOR: {
            AuditActionType.DIAGNOSTIC,
            AuditActionType.OPERATOR_DECISION,
        },
        AuditRole.CBS_DEVELOPER: {
            AuditActionType.ANALYSIS,
            AuditActionType.CODE_GENERATION,
        },
        AuditRole.SECURITY_ADMIN: {
            AuditActionType.SECURITY_SCRUB,
            AuditActionType.OPERATOR_DECISION,
        },
        AuditRole.AUDITOR: {
            AuditActionType.DIAGNOSTIC,
            AuditActionType.ANALYSIS,
            AuditActionType.CODE_GENERATION,
            AuditActionType.OPERATOR_DECISION,
            AuditActionType.SECURITY_SCRUB,
        },
    }

    @classmethod
    def check_permission(cls, role: AuditRole, action: AuditActionType) -> bool:
        """Vérifie si un rôle est habilité à exécuter une action donnée."""
        allowed = cls._role_permissions.get(role, set())
        return action in allowed

    @classmethod
    def record_event(
        cls,
        ticket_id: str,
        domain: str,
        action_type: AuditActionType,
        stan: str | None = None,
        operator_id: str = "system",
        role: AuditRole = AuditRole.MONETIQUE_OPERATOR,
        evidence_summary: list[str] | None = None,
        status: str = "SUCCESS",
        details: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Enregistre un événement auditable dans le journal immuable."""
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)

        record = AuditRecord(
            record_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
            ticket_id=ticket_id,
            stan=stan,
            domain=domain,
            action_type=action_type,
            operator_id=operator_id,
            role=role,
            evidence_summary=evidence_summary or [],
            status=status,
            details=details or {},
        )

        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.model_dump(by_alias=True), ensure_ascii=False) + "\n")

        return record

    @classmethod
    def get_trail(
        cls, ticket_id: str | None = None, domain: str | None = None
    ) -> list[AuditRecord]:
        """Récupère l'historique complet ou filtré par ticket/domaine."""
        if not AUDIT_FILE.exists():
            return []

        records: list[AuditRecord] = []
        with open(AUDIT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                    record = AuditRecord.model_validate(data)
                    if ticket_id and record.ticket_id != ticket_id:
                        continue
                    if domain and record.domain.upper() != domain.upper():
                        continue
                    records.append(record)
                except Exception:
                    continue
        return records
