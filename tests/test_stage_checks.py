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


def _expected_commands(stage_spec: dict[str, object]) -> list[tuple[str, int, tuple[str, ...]]]:
    if "ordered_stages" in stage_spec:
        command_specs = [
            command for ordered in stage_spec["ordered_stages"] for command in ordered["commands"]
        ]
    else:
        command_specs = stage_spec["commands"]

    return [
        (
            command_spec["command"],
            int(command_spec["timeout_seconds"]),
            tuple(command_spec.get("run_if_paths", [])),
        )
        for command_spec in command_specs
    ]


def test_stage_definitions_are_loaded_from_manifest() -> None:
    manifest = json.loads(
        Path("docs/process/quality_stage_commands.json").read_text(encoding="utf-8")
    )
    stages = MODULE._load_stages()

    assert set(stages) == set(manifest["stages"])
    for stage_name, stage_spec in manifest["stages"].items():
        expected = _expected_commands(stage_spec)
        actual = [
            (spec.command, spec.timeout_seconds, tuple(spec.run_if_paths))
            for spec in stages[stage_name].commands
        ]
        assert actual == expected


def test_ordered_stages_follow_manifest_order() -> None:
    manifest = json.loads(
        Path("docs/process/quality_stage_commands.json").read_text(encoding="utf-8")
    )
    stages = MODULE._load_stages()

    expected_order = [spec["id"] for spec in manifest["stages"]["qa-ci"]["ordered_stages"]]
    actual_order = [spec.id for spec in stages["qa-ci"].ordered_stages]

    assert actual_order == expected_order


def test_failure_file_extraction_is_deterministic() -> None:
    output = """src/core/engine.py:12: error: boom\ntests/test_invariants.py:9: error: fail\nsrc/core/engine.py:20: error: duplicate\n"""

    assert MODULE._first_failing_files(output) == ["src/core/engine.py", "tests/test_invariants.py"]


def test_stage_hooks_match_canonical_manifest() -> None:
    manifest = json.loads(
        Path("docs/process/quality_stage_commands.json").read_text(encoding="utf-8")
    )
    config_lines = Path(".pre-commit-config.yaml").read_text(encoding="utf-8").splitlines()

    for stage_spec in manifest["stages"].values():
        hook_spec = stage_spec.get("precommit_hook")
        if not isinstance(hook_spec, dict):
            continue

        block = _extract_hook_block(config_lines, hook_spec["id"])
        assert _extract_field(block, "entry") == hook_spec["entry"]
        assert _parse_inline_list(_extract_field(block, "stages")) == hook_spec["stages"]


def test_precommit_has_no_unmanaged_qa_stage_hooks() -> None:
    manifest = json.loads(
        Path("docs/process/quality_stage_commands.json").read_text(encoding="utf-8")
    )
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


def test_select_commands_docs_only_diff() -> None:
    stages = MODULE._load_stages()
    selected = MODULE._select_commands(
        "qa-commit",
        stages["qa-commit"],
        full_stage=False,
        changed_files=("docs/DEVELOPMENT.md",),
    )
    assert selected == ()


def test_select_commands_core_only_diff() -> None:
    stages = MODULE._load_stages()
    selected = MODULE._select_commands(
        "qa-commit",
        stages["qa-commit"],
        full_stage=False,
        changed_files=("src/core/engine.py",),
    )
    assert [spec.command for spec in selected] == [
        spec.command for spec in stages["qa-commit"].commands
    ]


def test_select_commands_mixed_diff() -> None:
    stages = MODULE._load_stages()
    selected = MODULE._select_commands(
        "qa-commit",
        stages["qa-commit"],
        full_stage=False,
        changed_files=("docs/DEVELOPMENT.md", "src/state_renormalization/model.py"),
    )
    assert [spec.command for spec in selected] == [
        spec.command for spec in stages["qa-commit"].commands
    ]


def test_select_commands_empty_staged_set_uses_full_stage() -> None:
    stages = MODULE._load_stages()
    selected = MODULE._select_commands(
        "qa-commit",
        stages["qa-commit"],
        full_stage=False,
        changed_files=(),
    )
    assert [spec.command for spec in selected] == [
        spec.command for spec in stages["qa-commit"].commands
    ]


def test_select_commands_qa_push_docs_only_diff() -> None:
    stages = MODULE._load_stages()
    selected = MODULE._select_commands(
        "qa-push",
        stages["qa-push"],
        full_stage=False,
        changed_files=("docs/DEVELOPMENT.md",),
    )
    assert selected == ()


def test_select_commands_qa_push_narrows_ruff_to_changed_python_files() -> None:
    stages = MODULE._load_stages()
    selected = MODULE._select_commands(
        "qa-push",
        stages["qa-push"],
        full_stage=False,
        changed_files=(
            "docs/DEVELOPMENT.md",
            "src/core/engine.py",
            "tests/test_invariants.py",
            "tests/test_invariants.py",
        ),
    )

    commands = [spec.command for spec in selected]
    assert commands[0] == "ruff check src/core/engine.py tests/test_invariants.py"
    assert commands[1] == "ruff format --check src/core/engine.py tests/test_invariants.py"
    assert commands[2:] == [
        "mypy --config-file=pyproject.toml src/state_renormalization src/core",
        "make program-sync",
        "pytest -q tests/test_engine_pending_obligation.py tests/test_invariants.py tests/test_contracts_decision_effect_shape.py",
    ]


def test_main_stops_on_first_blocking_failure_and_emits_reason(monkeypatch, capsys) -> None:
    fake_stages = {
        "qa-ci": MODULE.StageSpec(
            ordered_stages=(
                MODULE.OrderedStageSpec(
                    id="schema-validation",
                    stop_on_fail=True,
                    commands=(MODULE.CommandSpec(command="first", timeout_seconds=1),),
                ),
                MODULE.OrderedStageSpec(
                    id="heavy-suites",
                    stop_on_fail=True,
                    commands=(MODULE.CommandSpec(command="second", timeout_seconds=1),),
                ),
            ),
            commands=(
                MODULE.CommandSpec(command="first", timeout_seconds=1),
                MODULE.CommandSpec(command="second", timeout_seconds=1),
            ),
        )
    }
    ran_commands: list[str] = []

    def _fake_run(spec):
        ran_commands.append(spec.command)
        return MODULE.CommandResult(returncode=2)

    monkeypatch.setattr(MODULE, "_load_stages", lambda: fake_stages)
    monkeypatch.setattr(MODULE, "_run_command", _fake_run)
    monkeypatch.setattr(sys, "argv", ["run_stage_checks.py", "qa-ci"])

    result = MODULE.main()
    output = capsys.readouterr().out

    assert result == 2
    assert ran_commands == ["first"]
    reason = next(json.loads(line) for line in output.splitlines() if line.startswith("{"))
    assert reason == {
        "stage_id": "schema-validation",
        "reason_code": "command_failed",
        "next_action": "Rerun command locally: first",
    }
