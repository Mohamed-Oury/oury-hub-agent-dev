"""Points d'entrée de l'API pour les besoins Oracle FLEXCUBE."""

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path as PathParam, Response, status
from pydantic import BaseModel, Field

from agentic.agents.analysis_agent import (
    AgentError,
    InvalidOutputError,
    LLMConfigurationError,
    LLMUnavailableError,
    NeedRefusedError,
    run_analysis,
)
from agentic.agents.flexcube_code_agent import run_flexcube_code_generation
from agentic.core import config
from agentic.schemas.analysis import AnalysisResponse
from agentic.schemas.flexcube_code import FlexcubeCodeResponse
from agentic.schemas.flexcube_need import FlexcubeDevelopmentNeedInput
from agentic.services.analysis_store import (
    AlreadyDecidedError,
    AnalysisNotFoundError,
    AnalysisStore,
    MaxVersionsReachedError,
)
from agentic.services.prompt_builder import (
    build_flexcube_system_prompt,
    load_prompt,
    save_prompt,
    slugify,
)

router = APIRouter(prefix="/flexcube", tags=["flexcube"])

Name = Annotated[str, PathParam(pattern=r"^[a-z0-9-]+$", description="Identifiant du besoin")]


class PromptResponse(BaseModel):
    name: str = Field(description="Identifiant unique du besoin généré.")
    prompt: str = Field(description="Prompt système complet injecté à l'agent.")


class RejectBody(BaseModel):
    reason: str = Field(min_length=10, description="Motif du rejet motivé.")


@router.post("/prompts/generate", response_model=PromptResponse)
def generate_prompt(need: FlexcubeDevelopmentNeedInput) -> PromptResponse:
    prompt = build_flexcube_system_prompt(need)
    name = f"fcubs-{slugify(need.title)}"
    save_prompt(name, prompt, config.get_prompts_dir())
    return PromptResponse(name=name, prompt=prompt)


@router.post("/analyses/{name}", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
def create_initial_analysis(name: Name) -> AnalysisResponse:
    system_prompt = load_prompt(name, config.get_prompts_dir())
    if system_prompt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun prompt système trouvé sous le nom « {name} ».",
        )

    store = AnalysisStore(name, config.get_analyses_dir())
    if store.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Une analyse existe déjà pour « {name} ». Utilisez /reject ou /accept.",
        )

    try:
        result = run_analysis(system_prompt)
    except NeedRefusedError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
    except (LLMConfigurationError, LLMUnavailableError) as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error))
    except (InvalidOutputError, AgentError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))

    record = store.create_initial(result)
    return AnalysisResponse.from_record(name, record)


@router.get("/analyses/{name}", response_model=AnalysisResponse)
def get_analysis(name: Name) -> AnalysisResponse:
    store = AnalysisStore(name, config.get_analyses_dir())
    try:
        record = store.load_record()
    except AnalysisNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune analyse trouvée sous le nom « {name} ».",
        )
    return AnalysisResponse.from_record(name, record)


@router.post("/analyses/{name}/accept", response_model=AnalysisResponse)
def accept_analysis(name: Name) -> AnalysisResponse:
    store = AnalysisStore(name, config.get_analyses_dir())
    try:
        record = store.accept()
    except AnalysisNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune analyse trouvée sous le nom « {name} ».",
        )
    except AlreadyDecidedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    return AnalysisResponse.from_record(name, record)


@router.post("/analyses/{name}/reject", response_model=AnalysisResponse)
def reject_analysis(name: Name, body: RejectBody) -> AnalysisResponse:
    system_prompt = load_prompt(name, config.get_prompts_dir())
    if system_prompt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun prompt système trouvé sous le nom « {name} ».",
        )

    store = AnalysisStore(name, config.get_analyses_dir())
    try:
        rejected = store.prepare_retry(body.reason)
    except AnalysisNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune analyse trouvée sous le nom « {name} ».",
        )
    except AlreadyDecidedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    except MaxVersionsReachedError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))

    try:
        result = run_analysis(system_prompt, rejected=rejected)
    except NeedRefusedError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
    except (LLMConfigurationError, LLMUnavailableError) as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error))
    except (InvalidOutputError, AgentError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))

    record = store.append_rejected(result)
    return AnalysisResponse.from_record(name, record)


@router.post("/code/{name}", response_model=FlexcubeCodeResponse)
def generate_flexcube_code(name: Name) -> FlexcubeCodeResponse:
    system_prompt = load_prompt(name, config.get_prompts_dir())
    if system_prompt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun prompt système trouvé sous le nom « {name} ».",
        )

    store = AnalysisStore(name, config.get_analyses_dir())
    try:
        record = store.load_record()
    except AnalysisNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucune analyse trouvée sous le nom « {name} ».",
        )

    if record.decision != "ACCEPTEE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"L'analyse « {name} » doit être acceptée avant de générer le code PL/SQL.",
        )

    current_version = next((v for v in record.versions if v.version == record.current_version), None)
    if not current_version or not current_version.result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version courante d'analyse introuvable.",
        )

    try:
        code_result = run_flexcube_code_generation(system_prompt, current_version.result.sub_tasks)
    except (LLMConfigurationError, LLMUnavailableError) as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error))
    except (InvalidOutputError, AgentError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error))

    out_dir = config.get_analyses_dir().parent / "code"
    out_dir.mkdir(parents=True, exist_ok=True)
    pkg_file = out_dir / f"{name}_{code_result.package_name}.sql"
    pkg_file.write_text(
        f"-- SPECIFICATION\n{code_result.package_specification}\n/\n\n-- BODY\n{code_result.package_body}\n/",
        encoding="utf-8",
    )

    return FlexcubeCodeResponse.from_result(name, code_result, str(pkg_file))
