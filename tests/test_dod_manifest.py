from __future__ import annotations

import importlib.util
import json
import re
import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs" / "dod_manifest.json"

PR_TEMPLATE_PATH = ROOT / ".github" / "pull_request_template.md"
RENDER_SCRIPT_PATH = ROOT / ".github" / "scripts" / "render_transition_evidence.py"

_spec = importlib.util.spec_from_file_location("render_transition_evidence", RENDER_SCRIPT_PATH)
assert _spec and _spec.loader
render_transition_evidence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render_transition_evidence)


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


def _run_pytest_command(command: str) -> subprocess.CompletedProcess[str]:
    parts = shlex.split(command)
    return subprocess.run(
        parts,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _load_previous_manifest_from_git() -> dict | None:
    completed = subprocess.run(
        ["git", "show", "HEAD~1:docs/dod_manifest.json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return json.loads(completed.stdout)


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


def test_in_progress_capabilities_define_pytest_commands_over_existing_tests() -> None:
    manifest = _load_manifest()

    for cap in manifest["capabilities"]:
        if cap["status"] != "in_progress":
            continue

        commands = cap.get("pytest_commands", [])
        assert commands, f"In-progress capability {cap['id']} must define at least one pytest command"

        for command in commands:
            _assert_pytest_command_targets_existing_tests(command)


def test_in_progress_capabilities_have_executable_pytest_commands() -> None:
    manifest = _load_manifest()

    for cap in manifest["capabilities"]:
        if cap["status"] != "in_progress":
            continue

        commands = cap.get("pytest_commands", [])

        for command in commands:
            _assert_pytest_command_is_executable(command, cap["id"])


def test_done_status_transition_retains_at_least_one_passing_regression_command() -> None:
    previous_manifest = _load_previous_manifest_from_git()
    if previous_manifest is None:
        return

    previous_status_by_id = {
        cap["id"]: cap["status"]
        for cap in previous_manifest.get("capabilities", [])
    }

    current_manifest = _load_manifest()

    for cap in current_manifest["capabilities"]:
        if cap["status"] != "done":
            continue

        if previous_status_by_id.get(cap["id"]) == "done":
            continue

        commands = cap.get("pytest_commands", [])
        assert commands, (
            f"Capability {cap['id']} transitioned to done and must retain at least one regression pytest command"
        )

        passing_commands: list[str] = []
        for command in commands:
            _assert_pytest_command_targets_existing_tests(command)
            completed = _run_pytest_command(command)
            if completed.returncode == 0:
                passing_commands.append(command)

        assert passing_commands, (
            f"Capability {cap['id']} transitioned to done and must retain at least one passing pytest command\n"
            f"commands={commands}"
        )


def test_pull_request_template_autogen_section_matches_manifest_commands() -> None:
    manifest = _load_manifest()
    expected = render_transition_evidence._render_pr_template_autogen_section(manifest)
    template = PR_TEMPLATE_PATH.read_text(encoding="utf-8")

    start = template.find(render_transition_evidence.AUTOGEN_BEGIN)
    end = template.find(render_transition_evidence.AUTOGEN_END)

    assert start != -1 and end != -1 and end > start, "PR template must include AUTOGEN markers"

    actual = template[start : end + len(render_transition_evidence.AUTOGEN_END)]
    assert actual == expected, (
        "The AUTOGEN capability examples in .github/pull_request_template.md are out of date. "
        "Run: python .github/scripts/render_transition_evidence.py --regenerate-pr-template"
    )
