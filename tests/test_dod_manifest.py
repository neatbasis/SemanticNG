from __future__ import annotations

import json
import re
import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs" / "dod_manifest.json"


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _assert_pytest_command_targets_existing_tests(command: str) -> None:
    parts = shlex.split(command)
    assert parts and parts[0] == "pytest", f"Command must begin with pytest: {command}"
    test_paths = [part for part in parts[1:] if part.startswith("tests/")]
    assert test_paths, f"Command must include explicit tests paths: {command}"
    for p in test_paths:
        assert (ROOT / p).exists(), f"Missing referenced test path: {p}"


def _assert_pytest_command_is_executable(command: str, capability_id: str) -> None:
    parts = shlex.split(command)
    completed = subprocess.run(
        [*parts, "--collect-only"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    output = f"{completed.stdout}\n{completed.stderr}"
    assert completed.returncode == 0, (
        f"In-progress capability {capability_id} has a non-executable pytest command: {command}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
    assert re.search(r"(?:collected\s+(?!0\b)\d+\s+items?|(?<!0\s)\d+\s+tests?\s+collected)", output), (
        f"In-progress capability {capability_id} command did not collect any tests: {command}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )


def test_dod_manifest_exists_and_has_known_statuses() -> None:
    assert MANIFEST_PATH.exists(), "docs/dod_manifest.json must exist"
    manifest = _load_manifest()

    assert manifest.get("version") == 1
    statuses = manifest.get("statuses")
    assert statuses == ["done", "in_progress", "planned"]


def test_dod_manifest_capabilities_have_existing_code_paths() -> None:
    manifest = _load_manifest()
    valid_status = set(manifest["statuses"])

    for cap in manifest["capabilities"]:
        assert cap["status"] in valid_status, f"Unknown status for {cap['id']}"
        assert cap["roadmap_section"] in {"Now", "Next", "Later"}

        for p in cap["code_paths"]:
            assert (ROOT / p).exists(), f"Missing code path for {cap['id']}: {p}"


def test_done_capabilities_define_pytest_commands_over_existing_tests() -> None:
    manifest = _load_manifest()

    for cap in manifest["capabilities"]:
        if cap["status"] != "done":
            continue

        commands = cap.get("pytest_commands", [])
        assert commands, f"Done capability {cap['id']} must define at least one pytest command"

        for command in commands:
            _assert_pytest_command_targets_existing_tests(command)


def test_in_progress_capabilities_have_executable_pytest_commands() -> None:
    manifest = _load_manifest()

    for cap in manifest["capabilities"]:
        if cap["status"] != "in_progress":
            continue

        commands = cap.get("pytest_commands", [])
        assert commands, f"In-progress capability {cap['id']} must define at least one pytest command"

        for command in commands:
            _assert_pytest_command_targets_existing_tests(command)
            _assert_pytest_command_is_executable(command, cap["id"])
