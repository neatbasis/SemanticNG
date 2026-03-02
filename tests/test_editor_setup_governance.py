from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
README = ROOT / "README.md"
DEVELOPMENT = ROOT / "docs" / "DEVELOPMENT.md"
EDITOR_SETUP = ROOT / "docs" / "editor_setup.md"
VSCODE_SETTINGS = ROOT / ".vscode" / "settings.json"


def _canonical_mypy_tier1_command(pyproject_text: str) -> str:
    match = re.search(r"(?ms)^\[tool\.mypy\].*?^files\s*=\s*\[(.*?)\]", pyproject_text)
    assert match, "Could not locate [tool.mypy].files in pyproject.toml"
    scopes = re.findall(r'"([^"]+)"', match.group(1))
    assert scopes, "Expected at least one mypy Tier 1 file scope"
    return f"mypy --config-file=pyproject.toml {' '.join(scopes)}"


def test_editor_setup_artifacts_exist() -> None:
    assert VSCODE_SETTINGS.exists(), "Missing .vscode/settings.json"
    assert EDITOR_SETUP.exists(), "Missing docs/editor_setup.md"


def test_docs_include_first_five_minutes_sections() -> None:
    readme_text = README.read_text(encoding="utf-8")
    development_text = DEVELOPMENT.read_text(encoding="utf-8")

    assert "## First 5 minutes: verify editor diagnostics" in readme_text
    assert "## First 5 minutes: verify editor diagnostics" in development_text


def test_editor_governance_docs_reference_canonical_commands() -> None:
    pyproject_text = PYPROJECT.read_text(encoding="utf-8")
    expected_mypy_tier1 = _canonical_mypy_tier1_command(pyproject_text)

    docs_to_check = {
        "README.md": README.read_text(encoding="utf-8"),
        "docs/DEVELOPMENT.md": DEVELOPMENT.read_text(encoding="utf-8"),
        "docs/editor_setup.md": EDITOR_SETUP.read_text(encoding="utf-8"),
    }

    expected_commands = [
        "ruff check src tests",
        "ruff format --check src tests",
        expected_mypy_tier1,
    ]

    missing: list[str] = []
    for doc_name, doc_text in docs_to_check.items():
        for command in expected_commands:
            if command not in doc_text:
                missing.append(f"{doc_name} missing canonical command: {command}")

    assert not missing, "\n".join(missing)
