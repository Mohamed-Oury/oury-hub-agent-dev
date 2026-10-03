"""Sauvegarde et chargement du code 4GL généré."""

from pathlib import Path

from agentic.schemas.code import GeneratedCodeResult


def _path(name: str, directory: Path) -> Path:
    return directory / f"{name}_code.json"


def load_generated_code(name: str, directory: Path) -> GeneratedCodeResult | None:
    path = _path(name, directory)
    if not path.exists():
        return None
    return GeneratedCodeResult.model_validate_json(path.read_text(encoding="utf-8"))


def save_generated_code(name: str, result: GeneratedCodeResult, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = _path(name, directory)
    path.write_bytes(result.model_dump_json(by_alias=True, indent=2).encode("utf-8"))
    return path
