"""Schémas pour la génération de code Oracle FLEXCUBE (PL/SQL, DDL, Tests, Rollback)."""

from typing import Any
from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic.main import BaseModel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class FlexcubeGeneratedCodeResult(CamelModel):
    """Sortie structurée produite par l'agent de génération de code Oracle FLEXCUBE."""

    reasoning: str = Field(description="Raisonnement technique pas à pas pour la construction du code PL/SQL.")
    package_name: str = Field(description="Nom du package PL/SQL (ex: CUSPKS_VIREMENT_INTERA_CUSTOM).")
    package_specification: str = Field(description="Spécification complète du package PL/SQL (CREATE OR REPLACE PACKAGE).")
    package_body: str = Field(description="Corps complet du package PL/SQL (CREATE OR REPLACE PACKAGE BODY).")
    ddl_script: str | None = Field(default=None, description="Script DDL Oracle (tables, index, séquences, synonymes).")
    unit_test_plsql: str = Field(description="Script anonyme PL/SQL exécutable de tests unitaires avec assertions.")
    rollback_script: str = Field(description="Script de retour arrière propre (DROP/RESTORE) sans perte de données.")
    deployment_instructions: list[str] = Field(default_factory=list, description="Instructions d'exécution SQL*Plus ou déploiement.")
    validation_report: dict[str, Any] | None = Field(
        default=None, description="Rapport de validation syntaxique PL/SQL."
    )


class FlexcubeCodeResponse(CamelModel):
    """Réponse renvoyée par l'API de génération de code Oracle FLEXCUBE."""

    name: str = Field(description="Identifiant du besoin.")
    package_name: str = Field(description="Nom du package PL/SQL.")
    package_specification: str = Field(description="Spécification du package PL/SQL.")
    package_body: str = Field(description="Corps du package PL/SQL.")
    ddl_script: str | None = Field(default=None)
    unit_test_plsql: str = Field(description="Test unitaire PL/SQL.")
    rollback_script: str = Field(description="Script de rollback.")
    deployment_instructions: list[str] = Field(default_factory=list)
    validation_report: dict[str, Any] | None = Field(default=None)
    saved_path: str = Field(description="Chemin où le code est enregistré.")

    @classmethod
    def from_result(
        cls, name: str, result: FlexcubeGeneratedCodeResult, saved_path: str
    ) -> "FlexcubeCodeResponse":
        return cls(
            name=name,
            package_name=result.package_name,
            package_specification=result.package_specification,
            package_body=result.package_body,
            ddl_script=result.ddl_script,
            unit_test_plsql=result.unit_test_plsql,
            rollback_script=result.rollback_script,
            deployment_instructions=result.deployment_instructions,
            validation_report=result.validation_report,
            saved_path=saved_path,
        )
