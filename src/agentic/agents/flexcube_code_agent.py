"""Agent de génération de code Oracle FLEXCUBE (PL/SQL packages _CUSTOM, DDL, tests)."""

import json
from jinja2 import Environment, PackageLoader, StrictUndefined
from langchain.agents import create_agent
from langchain.agents.structured_output import StructuredOutputError
from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError
from pydantic import ValidationError

from agentic.agents.analysis_agent import (
    InvalidOutputError,
    LLMUnavailableError,
    build_chat_model,
)
from agentic.core import config
from agentic.schemas.analysis import SubTask
from agentic.schemas.flexcube_code import FlexcubeGeneratedCodeResult

_environment = Environment(
    loader=PackageLoader("agentic.prompts", "templates"),
    autoescape=False,
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


def run_flexcube_code_generation(
    system_prompt: str, sub_tasks: list[SubTask]
) -> FlexcubeGeneratedCodeResult:
    """Génère le package PL/SQL _CUSTOM, DDL et tests unitaires à partir des sous-tâches validées."""
    dumped = [t.model_dump(by_alias=True) for t in sub_tasks]
    sub_tasks_json = json.dumps(dumped, indent=2, ensure_ascii=False)

    code_prompt = _environment.get_template("flexcube_code_agent_prompt.md.j2").render(
        system_prompt=system_prompt,
        sub_tasks_json=sub_tasks_json,
    )

    agent = create_agent(
        build_chat_model(),
        tools=[],
        system_prompt=code_prompt,
        response_format=FlexcubeGeneratedCodeResult,
    )

    req = "Génère l'implémentation complète PL/SQL _CUSTOM, les scripts DDL, les tests unitaires et le rollback pour les sous-tâches validées."
    try:
        state = agent.invoke(
            {"messages": [HumanMessage(content=req)]},
            config={"recursion_limit": config.MAX_AGENT_STEPS},
        )
    except GraphRecursionError as error:
        raise InvalidOutputError(
            "Le modèle n'a pas produit de code PL/SQL conforme après plusieurs tentatives."
        ) from error
    except (StructuredOutputError, ValidationError) as error:
        raise InvalidOutputError(f"Code PL/SQL généré non conforme : {error}") from error

    output = state.get("structured_response")
    if not isinstance(output, FlexcubeGeneratedCodeResult):
        raise InvalidOutputError("Le modèle n'a renvoyé aucun code PL/SQL structuré.")

    return output
