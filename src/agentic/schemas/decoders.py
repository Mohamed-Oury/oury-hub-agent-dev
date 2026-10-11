"""Schémas Pydantic pour les Copilot Agents des Décodeurs Monétiques (EMV & ATM EJ)."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class EmvAnalysisInput(BaseModel):
    """Données transmises pour l'analyse Copilot EMV / DE55."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    input_hex: str = Field(..., description="Trame hexadécimale brute TLV du champ DE55.")
    tvr_raw: str | None = Field(default=None, description="Valeur hexadécimale brute du TVR (Tag 95).")
    parsed_tags_count: int = Field(default=0, description="Nombre de tags TLV identifiés.")
    critical_flags: list[str] = Field(
        default_factory=list, description="Liste des alertes critiques TVR extraites par le décodeur."
    )


class EmvAnalysisResult(BaseModel):
    """Restitution de l'expertise par l'Agent Copilot EMV."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    summary_title: str = Field(..., description="Synthèse succinte du diagnostic EMV.")
    crypto_type: str = Field(..., description="Type de cryptogramme détecté (ARQC, TC, AAC).")
    risk_level: Literal["FAIBLE", "MOYEN", "ÉLEVÉ", "CRITIQUE"] = Field(
        ..., description="Évaluation du niveau de risque de la transaction."
    )
    tvr_analysis_detail: str = Field(
        ..., description="Explication détaillée des anomalies identifiées par l'analyse bit-à-bit du TVR."
    )
    recommended_actions: list[str] = Field(
        default_factory=list, description="Actions curatives ou investigations recommandées."
    )
    copilot_explanation: str = Field(
        ..., description="Explication globale formulée en Français clair pour l'opérateur monétique."
    )


class AtmEjAnalysisInput(BaseModel):
    """Données transmises pour l'analyse Copilot Journal GAB (ATM EJ)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    raw_log: str = Field(..., description="Extrait du journal électronique GAB.")
    vendor: str = Field(default="GENERIC", description="Fabricant d'automate (NCR, DIEBOLD, WINCOR, HYOSUNG).")
    atm_id: str | None = Field(default=None, description="Identifiant unique du GAB / Terminal ID.")
    claim_advice: str = Field(
        default="UNKNOWN",
        description="Orientation brute calculée (FAVORABLE_RECREDIT, UNFAVORABLE_REJECT_CLAIM, INCONCLUSIVE).",
    )


class AtmEjAnalysisResult(BaseModel):
    """Restitution de l'expertise judiciaire par l'Agent Copilot ATM EJ."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    summary_title: str = Field(..., description="Titre synthétique de l'analyse du journal GAB.")
    vendor_detected: str = Field(..., description="Nom du constructeur et modèle d'automate.")
    hardware_fault_detected: bool = Field(
        ..., description="Indique si une panne mécanique/matérielle formelle est attestée."
    )
    forensic_chronology: list[str] = Field(
        default_factory=list, description="Horodatage reconstruit séquence par séquence."
    )
    claim_verdict_explanation: str = Field(
        ..., description="Conclusion juridiquement opposable pour le service Réclamations."
    )
    recommended_actions: list[str] = Field(
        default_factory=list, description="Contrôles complémentaires recommandés (Cassette rejet, Caméra)."
    )
    copilot_explanation: str = Field(
        ..., description="Synthèse explicative rédigée en langage naturel."
    )
