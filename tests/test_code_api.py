from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agentic.api.main import app
from agentic.api.v1.code import get_code_runner
from agentic.core.config import get_analyses_dir, get_code_dir, get_output_dir
from agentic.schemas.analysis import AnalysisResult, AnalysisVersion, SubTask
from agentic.schemas.code import GeneratedCodeResult
from agentic.services.analysis_store import save_versions
from agentic.services.prompt_builder import save_prompt

NAME = "test-code-gen"
CODE_URL = f"/api/v1/code/{NAME}"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app.dependency_overrides[get_output_dir] = lambda: tmp_path / "prompts"
    app.dependency_overrides[get_analyses_dir] = lambda: tmp_path / "analyses"
    app.dependency_overrides[get_code_dir] = lambda: tmp_path / "code"

    mock_result = GeneratedCodeResult(
        reasoning="Test reasoning for 4GL generation.",
        program_name="p_cbs_test.4gl",
        code_4gl="DATABASE amplitude\nMAIN\n    DISPLAY 'OK'\nEND MAIN",
        screen_name="f_cbs_test.per",
        code_per="LAYOUT\n    GRID\n    { [f00] }\n    END\nEND",
        sql_script="-- Test SQL",
        compilation_instructions=["c4gl -o p_cbs_test p_cbs_test.4gl"],
        unit_test_script=["./p_cbs_test"],
    )
    app.dependency_overrides[get_code_runner] = lambda: lambda prompt, tasks: mock_result

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_code_generation_fails_if_prompt_missing(client: TestClient) -> None:
    assert client.post(CODE_URL).status_code == 404


def test_code_generation_fails_if_analysis_not_accepted(client: TestClient, tmp_path: Path) -> None:
    save_prompt(NAME, "Prompt test", tmp_path / "prompts")
    version = AnalysisVersion(
        version=1,
        decision="EN_ATTENTE",
        created_at="2026-10-03T14:00:00Z",
        result=AnalysisResult(
            analysis={
                "summary": "Summary",
                "businessObjective": "Obj",
                "actors": ["User"],
                "preconditions": [],
                "postconditions": [],
                "businessRules": [],
                "requiredData": [],
                "cbsDependencies": [],
                "unresolvedQuestions": [],
                "technicalRisks": [],
            },
            sub_tasks=[
                SubTask(
                    id="TASK-01",
                    title="Task 1",
                    description="Desc",
                    type="4GL",
                    priority="HAUTE",
                    dependencies=[],
                    estimation="1 jour",
                    inputs="In",
                    outputs="Out",
                    acceptanceCriteria=["OK"],
                    concernedFiles=["p_cbs_test.4gl"],
                )
            ],
        ),
    )
    save_versions(NAME, [version], tmp_path / "analyses")

    response = client.post(CODE_URL)
    assert response.status_code == 409
    assert "doit être acceptée" in response.json()["detail"]


def test_code_generation_succeeds_when_accepted(client: TestClient, tmp_path: Path) -> None:
    save_prompt(NAME, "Prompt test", tmp_path / "prompts")
    version = AnalysisVersion(
        version=1,
        decision="ACCEPTEE",
        created_at="2026-10-03T14:00:00Z",
        result=AnalysisResult(
            analysis={
                "summary": "Summary",
                "businessObjective": "Obj",
                "actors": ["User"],
                "preconditions": [],
                "postconditions": [],
                "businessRules": [],
                "requiredData": [],
                "cbsDependencies": [],
                "unresolvedQuestions": [],
                "technicalRisks": [],
            },
            sub_tasks=[
                SubTask(
                    id="TASK-01",
                    title="Task 1",
                    description="Desc",
                    type="4GL",
                    priority="HAUTE",
                    dependencies=[],
                    estimation="1 jour",
                    inputs="In",
                    outputs="Out",
                    acceptanceCriteria=["OK"],
                    concernedFiles=["p_cbs_test.4gl"],
                    status="VALIDE",
                )
            ],
        ),
    )
    save_versions(NAME, [version], tmp_path / "analyses")

    response = client.post(CODE_URL)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == NAME
    assert data["programName"] == "p_cbs_test.4gl"
    assert "DATABASE amplitude" in data["code4Gl"]
    assert "LAYOUT" in data["codePer"]

    # Test GET route
    get_res = client.get(CODE_URL)
    assert get_res.status_code == 200
    assert get_res.json()["programName"] == "p_cbs_test.4gl"
