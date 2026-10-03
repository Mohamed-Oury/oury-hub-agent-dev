"""Routes de l'agent de génération de code 4GL & .per."""

from collections.abc import Callable
from pathlib import Path as FilePath
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from agentic.agents.analysis_agent import (
    InvalidOutputError,
    LLMConfigurationError,
    LLMUnavailableError,
)
from agentic.agents.code_agent import run_code_generation
from agentic.core.config import get_analyses_dir, get_code_dir, get_output_dir
from agentic.schemas.analysis import SubTask
from agentic.schemas.code import CodeResponse, GeneratedCodeResult
from agentic.services.analysis_store import load_versions
from agentic.services.code_store import load_generated_code, save_generated_code
from agentic.services.prompt_builder import load_prompt

router = APIRouter(prefix="/api/v1/code", tags=["code"])

CodeRunner = Callable[[str, list[SubTask]], GeneratedCodeResult]


def get_code_runner() -> CodeRunner:
    return run_code_generation


Name = Annotated[str, Path(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")]
PromptsDir = Annotated[FilePath, Depends(get_output_dir)]
AnalysesDir = Annotated[FilePath, Depends(get_analyses_dir)]
CodeDir = Annotated[FilePath, Depends(get_code_dir)]
Runner = Annotated[CodeRunner, Depends(get_code_runner)]

ERRORS = {
    404: {"description": "Prompt, analyse ou code généré introuvable."},
    409: {"description": "L'analyse doit être acceptée avant de pouvoir générer le code."},
    502: {"description": "Sortie du modèle non conforme au schéma."},
    503: {"description": "Fournisseur LLM non configuré ou injoignable."},
}


@router.post(
    "/{name}",
    summary="Générer le code 4GL et écran .per à partir des sous-tâches validées",
    responses=ERRORS,
)
def generate_code(
    name: Name,
    prompts_dir: PromptsDir,
    analyses_dir: AnalysesDir,
    code_dir: CodeDir,
    runner: Runner,
) -> CodeResponse:
    prompt = load_prompt(name, prompts_dir)
    if prompt is None:
        raise HTTPException(
            404, f"Prompt « {name} » introuvable. Générez-le avec /api/v1/prompts/generate."
        )

    versions = load_versions(name, analyses_dir)
    if not versions:
        raise HTTPException(404, f"Aucune analyse pour « {name} ».")

    latest = versions[-1]
    if latest.decision != "ACCEPTEE":
        msg = f"L'analyse de « {name} » doit être acceptée (statut : {latest.decision})."
        raise HTTPException(409, msg)

    validated_tasks = [task for task in latest.result.sub_tasks if task.status == "VALIDE"]
    if not validated_tasks:
        validated_tasks = latest.result.sub_tasks

    try:
        result = runner(prompt, validated_tasks)
    except InvalidOutputError as error:
        raise HTTPException(502, str(error)) from error
    except (LLMConfigurationError, LLMUnavailableError) as error:
        raise HTTPException(503, str(error)) from error

    saved_path = save_generated_code(name, result, code_dir)
    return CodeResponse.from_result(name, result, str(saved_path))


@router.get("/{name}", summary="Obtenir le dernier code 4GL généré", responses=ERRORS)
def get_code(name: Name, code_dir: CodeDir) -> CodeResponse:
    result = load_generated_code(name, code_dir)
    if result is None:
        msg = f"Aucun code généré pour « {name} ». Lancez d'abord POST /api/v1/code/{name}."
        raise HTTPException(404, msg)
    saved_path = code_dir / f"{name}_code.json"
    return CodeResponse.from_result(name, result, str(saved_path))
