"""Point d'accès API pour le Monétique Diagnostic Copilot Agent (V1)."""

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from agentic.agents.diagnostic_agent import MonetiqueDiagnosticAgent
from agentic.schemas.diagnostic import DiagnosticInput, DiagnosticResult

router = APIRouter(prefix="/api/v1/diagnostic", tags=["diagnostic"])
agent = MonetiqueDiagnosticAgent()


@router.post(
    "/analyze",
    response_model=DiagnosticResult,
    summary="Analyse d'incident monétique par le Diagnostic Copilot Agent",
    description=(
        "Analyse un incident à travers la chaîne monétique (ATM -> Switch -> Host -> CBS), "
        "reconstruit le flux, identifie le point de rupture, formule des hypothèses probabilisées "
        "et soumet une RCA sous réserve de validation humaine obligatoire."
    ),
)
def analyze_incident(input_data: DiagnosticInput) -> DiagnosticResult:
    try:
        return agent.run_diagnostic(input_data)
    except ValidationError as err:
        raise HTTPException(
            status_code=422,
            detail=f"Erreur de validation des données d'entrée : {err}",
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'exécution du diagnostic agentic : {err}",
        ) from err
