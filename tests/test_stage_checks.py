from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts/ci/run_stage_checks.py"
SPEC = importlib.util.spec_from_file_location("run_stage_checks", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _extract_hook_block(config_lines: list[str], hook_id: str) -> list[str]:
    hook_pattern = re.compile(rf"^(\s*)-\s+id:\s+{re.escape(hook_id)}\s*$")
    start_index = -1
    hook_indent = ""

    for idx, line in enumerate(config_lines):
        match = hook_pattern.match(line)
        if match:
            start_index = idx
            hook_indent = match.group(1)
            break

    assert start_index >= 0, f"Missing hook id '{hook_id}'"

    block: list[str] = []
    for line in config_lines[start_index + 1 :]:
        if re.match(rf"^{re.escape(hook_indent)}-\s+id:\s+", line):
            break
        block.append(line)

    return block


def _extract_field(block: list[str], key: str) -> str:
    for line in block:
        stripped = line.strip()
        if stripped.startswith(f"{key}:"):
            return stripped.split(":", maxsplit=1)[1].strip()
    raise AssertionError(f"Hook block missing '{key}'")


def _parse_inline_list(value: str) -> list[str]:
    assert value.startswith("[") and value.endswith("]")
    body = value[1:-1].strip()
    if not body:
        return []
    return [part.strip().strip("\"'") for part in body.split(",") if part.strip()]


def test_stage_definitions_are_loaded_from_manifest() -> None:
    manifest = json.loads(Path("docs/process/quality_stage_commands.json").read_text(encoding="utf-8"))
    stages = MODULE._load_stages()

    assert set(stages) == set(manifest["stages"])
    for stage_name, stage_spec in manifest["stages"].items():
        expected = [
            (command_spec["command"], int(command_spec["timeout_seconds"]))
            for command_spec in stage_spec["commands"]
        ]
        actual = [(spec.command, spec.timeout_seconds) for spec in stages[stage_name].commands]
        assert actual == expected


def test_failure_file_extraction_is_deterministic() -> None:
    output = """src/core/engine.py:12: error: boom\ntests/test_invariants.py:9: error: fail\nsrc/core/engine.py:20: error: duplicate\n"""

    assert MODULE._first_failing_files(output) == ["src/core/engine.py", "tests/test_invariants.py"]


def test_stage_hooks_match_canonical_manifest() -> None:
    manifest = json.loads(Path("docs/process/quality_stage_commands.json").read_text(encoding="utf-8"))
    config_lines = Path(".pre-commit-config.yaml").read_text(encoding="utf-8").splitlines()

    for stage_spec in manifest["stages"].values():
        hook_spec = stage_spec.get("precommit_hook")
        if not isinstance(hook_spec, dict):
            continue

        block = _extract_hook_block(config_lines, hook_spec["id"])
        assert _extract_field(block, "entry") == hook_spec["entry"]
        assert _parse_inline_list(_extract_field(block, "stages")) == hook_spec["stages"]


def test_precommit_has_no_unmanaged_qa_stage_hooks() -> None:
    manifest = json.loads(Path("docs/process/quality_stage_commands.json").read_text(encoding="utf-8"))
    config_lines = Path(".pre-commit-config.yaml").read_text(encoding="utf-8").splitlines()

    expected_hook_ids = {
        stage_spec["precommit_hook"]["id"]
        for stage_spec in manifest["stages"].values()
        if isinstance(stage_spec.get("precommit_hook"), dict)
    }
    configured_hook_ids = {
        match.group(1)
        for line in config_lines
        if (match := re.match(r"^\s*-\s+id:\s+(qa-[a-z0-9-]+-stage)\s*$", line))
    }

    assert configured_hook_ids == expected_hook_ids
