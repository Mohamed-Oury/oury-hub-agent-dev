"""Modèles d'entrée pour les besoins de développement Oracle FLEXCUBE."""

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

InlineText = Annotated[
    str, StringConstraints(min_length=2, max_length=500, pattern=r"^[^<>\r\n]+$")
]
FreeText = Annotated[str, StringConstraints(max_length=200000)]

FlexcubeModule = Literal["ST", "AC", "GL", "CL", "FT", "LC", "DE", "GW", "AEOD", "AUTRE"]
FlexcubeVersion = Literal["12.4", "14.x", "UNCONFIRMED"]
FlexcubeEnvironment = Literal["PLSQL_BACKEND", "GATEWAY_INTERFACE", "BATCH_AEOD", "RADPACK_EXT"]

EXAMPLE_FLEXCUBE_NEED = {
    "title": "Virement interne entre deux comptes avec contrôle de solde",
    "functionalDescription": (
        "L'opérateur ou un flux automate initie un débit d'un compte émetteur vers un compte bénéficiaire. "
        "Le système vérifie la provision dans STTM_CUST_ACCOUNT, crée l'événement dans FTTB_CONTRACT_MASTER "
        "et journalise les mouvements comptables dans ACTB_DAILY_LOG."
    ),
    "module": "FT",
    "targetUsers": "Gestionnaire d'agence / Automate de virements",
    "knownBusinessRules": (
        "Tables concernées : STTM_CUST_ACCOUNT (ACY_AVL_BAL, AC_STAT_NO_DR), ACTB_DAILY_LOG, FTTB_CONTRACT_MASTER. "
        "Le montant doit être > 0. Verrouillage du compte débiteur avec NOWAIT pour éviter les blocages ORA-00054."
    ),
    "inputData": ["Code agence", "Compte débit", "Compte crédit", "Montant", "Devise", "Motif"],
    "specialConstraints": "Pas de COMMIT dans le package _CUSTOM, gestion d'exception standard ST-SAVE-001.",
    "flexcubeVersion": "14.x",
    "environmentType": "PLSQL_BACKEND",
}


class FlexcubeDevelopmentNeedInput(BaseModel):
    """Besoin de développement Oracle FLEXCUBE soumis par l'ingénieur."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={"examples": [EXAMPLE_FLEXCUBE_NEED]},
    )

    title: InlineText = Field(description="Titre du besoin / User Story FCUBS.")
    functional_description: FreeText = Field(min_length=20, description="Description détaillée du besoin bancaire.")
    module: str = Field(default="FT", description="Module Oracle FLEXCUBE (ST, AC, GL, CL, FT, LC, DE, GW, AEOD).")
    target_users: FreeText = Field(min_length=2, description="Profils utilisateurs cibles ou services consommateurs.")
    known_business_rules: FreeText = Field(
        min_length=2,
        description="Règles métier identifiées, tables FCUBS et colonnes où intervenir.",
    )
    input_data: list[Annotated[str, StringConstraints(min_length=1, max_length=500)]] = Field(
        min_length=1, max_length=50, description="Données et paramètres en entrée."
    )
    special_constraints: FreeText | None = Field(
        default=None, description="Contraintes spécifiques (NOWAIT, SLA latence, transaction ACID, batch)."
    )
    flexcube_version: InlineText = Field(default="14.x", description="Version d'Oracle FLEXCUBE.")
    environment_type: InlineText = Field(
        default="PLSQL_BACKEND",
        description="Environnement technique (PLSQL_BACKEND, GATEWAY_INTERFACE, BATCH_AEOD, RADPACK_EXT).",
    )
    existing_package_name: InlineText | None = Field(
        default=None, description="Nom du package PL/SQL existant à étendre ou modifier (ex: stpks_cust_*.sql)."
    )
