"""Point d'accès API pour les Copilot Agents des Décodeurs Monétiques (EMV & ATM EJ)."""

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from agentic.agents.decoders_agent import AtmEjCopilotAgent, EmvCopilotAgent
from agentic.schemas.decoders import (
    AtmEjAnalysisInput,
    AtmEjAnalysisResult,
    EmvAnalysisInput,
    EmvAnalysisResult,
)

router = APIRouter(prefix="/api/v1/decoders", tags=["decoders"])

emv_agent = EmvCopilotAgent()
atm_ej_agent = AtmEjCopilotAgent()


@router.post(
    "/emv/analyze",
    response_model=EmvAnalysisResult,
    summary="Analyse de sécurité EMV / DE55 par l'Agent Copilot",
    description="Analyse experte du TVR Tag 95, des cryptogrammes et du niveau de risque EMV.",
)
def analyze_emv(input_data: EmvAnalysisInput) -> EmvAnalysisResult:
    try:
        return emv_agent.analyze(input_data)
    except ValidationError as err:
        raise HTTPException(
            status_code=422,
            detail=f"Erreur de validation des données d'entrée EMV : {err}",
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'exécution du Copilot Agent EMV : {err}",
        ) from err


@router.post(
    "/atm-ej/analyze",
    response_model=AtmEjAnalysisResult,
    summary="Analyse judiciaire / forensic du Journal GAB par l'Agent Copilot",
    description="Analyse des logs capteurs, chronologie des événements et avis opposable pour réclamations.",
)
def analyze_atm_ej(input_data: AtmEjAnalysisInput) -> AtmEjAnalysisResult:
    try:
        return atm_ej_agent.analyze(input_data)
    except ValidationError as err:
        raise HTTPException(
            status_code=422,
            detail=f"Erreur de validation des données d'entrée ATM EJ : {err}",
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'exécution du Copilot Agent ATM EJ : {err}",
        ) from err
