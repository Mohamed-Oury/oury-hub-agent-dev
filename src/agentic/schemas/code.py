"""Schémas pour la génération de code 4GL et écran .per."""

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic.main import BaseModel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class GeneratedCodeResult(CamelModel):
    """Sortie structurée produite par l'agent de génération de code."""

    reasoning: str = Field(description="Raisonnement pas à pas pour la construction du code.")
    program_name: str = Field(description="Nom du fichier 4GL (ex: p_cbs_bktra_flx.4gl).")
    code_4gl: str = Field(description="Code source Informix-4GL complet et valide.")
    screen_name: str | None = Field(
        default=None, description="Nom du fichier écran .per (ex: f_cbs_bktra_flx.per)."
    )
    code_per: str | None = Field(
        default=None, description="Code source .per interactif Web (LAYOUT, GRID)."
    )
    sql_script: str | None = Field(
        default=None, description="Script SQL d'accompagnement (index, tables)."
    )
    compilation_instructions: list[str] = Field(
        default_factory=list, description="Commandes de compilation Unix AIX."
    )
    unit_test_script: list[str] = Field(
        default_factory=list, description="Scénarios de test unitaire."
    )


class CodeResponse(CamelModel):
    """Réponse renvoyée par l'API de génération de code."""

    name: str = Field(description="Identifiant du besoin.")
    program_name: str = Field(description="Nom du programme 4GL.")
    code_4gl: str = Field(description="Code source Informix-4GL généré.")
    screen_name: str | None = Field(default=None, description="Nom de l'écran .per.")
    code_per: str | None = Field(default=None, description="Code source de l'écran .per.")
    sql_script: str | None = Field(default=None, description="Script SQL.")
    compilation_instructions: list[str] = Field(default_factory=list)
    unit_test_script: list[str] = Field(default_factory=list)
    saved_path: str = Field(description="Chemin où le code est enregistré.")

    @classmethod
    def from_result(
        cls, name: str, result: GeneratedCodeResult, saved_path: str
    ) -> "CodeResponse":
        return cls(
            name=name,
            program_name=result.program_name,
            code_4gl=result.code_4gl,
            screen_name=result.screen_name,
            code_per=result.code_per,
            sql_script=result.sql_script,
            compilation_instructions=result.compilation_instructions,
            unit_test_script=result.unit_test_script,
            saved_path=saved_path,
        )
