"""Schémas Pydantic pour le Monétique Diagnostic Copilot Agent (Investigation Agentic Disciplinée)."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class DiagnosticInput(BaseModel):
    """Données d'entrée saisies ou transmises pour l'analyse de diagnostic."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Titre ou résumé succinct de l'incident monétique.",
    )
    domain: str = Field(
        default="GAB",
        description="Domaine d'activité (GAB, TPE, CARTE, INTERFACE, PAYWAY, HOST, CLEARING).",
    )
    severity: str = Field(
        default="HIGH",
        description="Niveau de criticité (LOW, MEDIUM, HIGH, CRITICAL).",
    )
    symptom: str = Field(
        ...,
        description="Symptôme constaté ou message d'erreur rapporté par l'utilisateur/automate.",
    )
    facts: str | None = Field(
        default=None,
        description="Faits mesurables observés (volumétrie, taux d'échec, tranches horaires).",
    )
    stan: str | None = Field(
        default=None,
        description="Audit Trail Number (STAN) ou numéro de référence RRN.",
    )
    error_code: str | None = Field(
        default=None,
        description="Code erreur ou DE39 / MTI identifié (ex: DE39=91, MTI=0200).",
    )
    raw_logs: str | None = Field(
        default=None,
        description="Extrait de logs système, trames ISO 8583 brutes ou nouveaux logs d'investigation.",
    )
    scope: str | None = Field(
        default=None,
        description="Périmètre technique ou géographique impacté.",
    )


class TransactionHop(BaseModel):
    """Étape ou sous-système traversé par la transaction monétique."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    component: str = Field(..., description="Nom du composant (ATM, SWITCH, HOST, CBS, HSM).")
    status: Literal["OK", "TIMEOUT", "ERROR", "PENDING"] = Field(
        ..., description="Statut du traitement au niveau de ce composant."
    )
    timestamp: str | None = Field(default=None, description="Horodatage ISO de passage.")
    details: str = Field(..., description="Description de l'action exécutée.")
    mti: str | None = Field(default=None, description="MTI échangé le cas échéant.")
    de39: str | None = Field(default=None, description="Code DE39 retourné s'il existe.")


class TimelineEvent(BaseModel):
    """Événement précis dans la séquence d'exécution."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    time: str = Field(..., description="Horodatage de l'événement.")
    source: str = Field(..., description="Composant émetteur.")
    destination: str = Field(..., description="Composant destinataire.")
    mti: str | None = Field(default=None, description="MTI ISO 8583.")
    de39: str | None = Field(default=None, description="Code réponse DE39.")
    status: str = Field(..., description="Résultat de l'interaction.")
    description: str = Field(..., description="Explication détaillée.")


class DiagnosticHypothesis(BaseModel):
    """Hypothèse formulée par l'agent avec score d'appui et décomposition des causes."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str = Field(..., description="Identifiant unique (ex: H1, H2).")
    title: str = Field(..., description="Intitulé de l'hypothèse.")
    confidence_level: Literal["TRÈS ÉLEVÉE", "ÉLEVÉE", "MOYENNE", "FAIBLE"] = Field(
        ..., description="Évaluation rigoureuse du niveau de confiance."
    )
    supporting_evidence_count: int = Field(default=0, description="Nombre de preuves appuyant l'hypothèse.")
    contradicting_evidence_count: int = Field(default=0, description="Nombre de faits la contredisant.")
    missing_evidence_count: int = Field(default=0, description="Nombre de preuves manquantes.")
    status: Literal["PROPOSED", "INVESTIGATING", "SUPPORTED", "CONFIRMED", "REJECTED"] = Field(
        default="PROPOSED", description="Statut de validation de l'hypothèse."
    )
    evidence_details: list[str] = Field(
        default_factory=list, description="Liste des faits/logs appuyant cette piste."
    )
    potential_causes: list[str] = Field(
        default_factory=list, description="Causes techniques sous-jacentes possibles."
    )
    rationale: str = Field(..., description="Explication du raisonnement agentic.")


class SimilarIncident(BaseModel):
    """Incident similaire trouvé dans la base de connaissances (Référence Historique)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    reference: str = Field(..., description="Référence de l'incident (ex: INC-024).")
    title: str = Field(..., description="Titre de l'incident passé.")
    symptom: str = Field(..., description="Symptôme similaire constaté.")
    breakpoint: str = Field(..., description="Point de rupture identifié.")
    root_cause: str = Field(..., description="Cause racine formellement validée dans le passé.")
    resolution: str = Field(..., description="Action corrective efficace appliquée.")
    similarity_percent: int = Field(..., ge=0, le=100, description="Niveau de correspondance.")


class EvidenceItem(BaseModel):
    """Élément de preuve collecté pour l'incident courant."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    source: str = Field(..., description="Source de l'information (Logs, DE39, ISO, Database).")
    type: str = Field(..., description="Type de preuve (Log, Code, Reference, Trace).")
    content: str = Field(..., description="Contenu lisible de la preuve.")
    is_verified: bool = Field(default=True, description="Vérification effectuée.")
    timestamp: str | None = Field(default=None, description="Horodatage s'il y a lieu.")


class EvidenceLedgerItem(BaseModel):
    """Entrée normalisée du registre des preuves avec typage strict."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str = Field(..., description="ID unique (ex: E01, E02).")
    information: str = Field(..., description="Énoncé de l'information.")
    source: str = Field(..., description="Origine (Incident Courant, Agent Inférence, ISO, KB Historique).")
    type: Literal["VERIFIED_EVIDENCE", "INFERENCE", "HISTORICAL_REFERENCE", "REJECTED_CONTRADICTION"] = Field(
        ..., description="Catégorie formelle normalisée de l'élément."
    )
    status: Literal["VALIDATED_FACT", "HYPOTHESIS_INFERENCE", "HISTORICAL_ONLY", "CONTRADICTION_REJECTED"] = Field(
        ..., description="Statut de validité dans l'analyse courante."
    )
    rationale: str = Field(..., description="Justification de la prise en compte ou du rejet.")


class RcaProposal(BaseModel):
    """Proposition de Cause Racine nécessitant obligatoirement la validation de l'opérateur."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    summary: str = Field(..., description="Résumé synthétique de la cause racine proposée.")
    status: Literal["PROPOSED_UNCONFIRMED", "CONFIRMED_BY_OPERATOR", "REJECTED_BY_OPERATOR"] = Field(
        default="PROPOSED_UNCONFIRMED",
        description="Garde-fou humain : statut d'approbation par l'opérateur.",
    )
    confidence_level: Literal["TRÈS ÉLEVÉE", "ÉLEVÉE", "MOYENNE", "FAIBLE"] = Field(
        default="MOYENNE", description="Degré de certitude de l'agent."
    )
    recommended_actions: list[str] = Field(
        default_factory=list, description="Actions curatives recommandées."
    )
    human_validation_required: bool = Field(
        default=True, description="Indique si la validation humaine est indispensable (toujours True)."
    )


class InitialAnalysis(BaseModel):
    """Enrichissement et classification initiale de l'incident."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    detected_domain: str = Field(..., description="Domaine fonctionnel détecté.")
    channel: str = Field(..., description="Canal monétique identifié (ATM, POS, WEB).")
    probable_type: str = Field(..., description="Type de transaction (ex: Financial Transaction 0200).")
    potential_mti: str = Field(..., description="MTI ISO 8583 suggéré.")
    symptom_summary: str = Field(..., description="Synthèse clarifiée du dysfonctionnement.")
    suspect_components: list[str] = Field(..., description="Composants suspects par ordre de priorité.")
    confidence_score: int = Field(..., ge=0, le=100, description="Confiance initiale en %.")


class DiagnosticResult(BaseModel):
    """Résultat complet de l'analyse produite par le Monétique Diagnostic Copilot Agent."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    initial_analysis: InitialAnalysis
    flow_mapping: list[TransactionHop]
    breakpoint_analysis: str
    potential_technical_causes: list[str] = Field(
        default_factory=list, description="Causes techniques sous-jacentes identifiées au point de rupture."
    )
    timeline: list[TimelineEvent]
    hypotheses: list[DiagnosticHypothesis]
    similar_incidents: list[SimilarIncident]
    evidence_list: list[EvidenceItem]
    evidence_ledger: list[EvidenceLedgerItem] = Field(
        default_factory=list, description="Registre structuré des preuves et déductions."
    )
    contradictions_detected: list[str] = Field(
        default_factory=list, description="Liste des contradictions détectées et éliminées."
    )
    missing_evidence: list[str] = Field(
        default_factory=list, description="Checklist des preuves manquantes indispensables pour valider la RCA."
    )
    next_investigation_step: str = Field(
        ..., description="Prochaine action d'investigation recommandée à l'opérateur."
    )
    rca_proposal: RcaProposal
    tools_called: list[str] = Field(
        default_factory=list, description="Liste des outils de diagnostic invoqués."
    )
