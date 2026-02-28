from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "scripts" / "render_transition_evidence.py"

_spec = importlib.util.spec_from_file_location("render_transition_evidence", SCRIPT_PATH)
assert _spec and _spec.loader
render_transition_evidence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render_transition_evidence)


def test_status_transitions_detects_changed_capability_statuses() -> None:
    base_manifest = {
        "capabilities": [
            {"id": "cap_a", "status": "in_progress"},
            {"id": "cap_b", "status": "done"},
        ]
    }
    head_manifest = {
        "capabilities": [
            {"id": "cap_a", "status": "done"},
            {"id": "cap_b", "status": "done"},
            {"id": "cap_c", "status": "in_progress"},
        ]
    }

    transitioned = render_transition_evidence._status_transitions(base_manifest, head_manifest)

    assert transitioned == {"cap_a"}


def test_transitioned_capability_commands_filters_to_transitioned_and_non_empty_strings() -> None:
    head_manifest = {
        "capabilities": [
            {
                "id": "cap_a",
                "pytest_commands": ["pytest tests/test_alpha.py", "", None, "pytest tests/test_beta.py"],
            },
            {"id": "cap_b", "pytest_commands": ["pytest tests/test_gamma.py"]},
        ]
    }

    commands = render_transition_evidence._transitioned_capability_commands(head_manifest, {"cap_a"})

    assert commands == {
        "cap_a": [
            "pytest tests/test_alpha.py",
            "pytest tests/test_beta.py",
        ]
    }


def test_render_block_includes_expected_markers_and_evidence_lines() -> None:
    block = render_transition_evidence._render_block(
        {
            "cap_a": ["pytest tests/test_alpha.py"],
            "cap_b": ["pytest tests/test_beta.py"],
        }
    )

    assert "<!-- transition-evidence:start -->" in block
    assert "<!-- transition-evidence:end -->" in block
    assert "#### cap_a" in block
    assert "pytest tests/test_alpha.py" in block
    assert "Evidence: https://example.com/replace-with-evidence/cap_a/1" in block


def test_render_block_reports_no_transitions_message_when_empty() -> None:
    block = render_transition_evidence._render_block({})

    assert "No capability status transitions were detected for this diff." in block


def test_render_pr_template_autogen_section_is_sorted_and_wrapped() -> None:
    manifest = {
        "capabilities": [
            {"id": "zeta", "pytest_commands": ["pytest tests/test_zeta.py"]},
            {"id": "alpha", "pytest_commands": ["pytest tests/test_alpha.py", "pytest tests/test_alpha_extra.py"]},
            {"id": "empty", "pytest_commands": []},
        ]
    }

    section = render_transition_evidence._render_pr_template_autogen_section(manifest)

    assert section.startswith(render_transition_evidence.AUTOGEN_BEGIN)
    assert section.endswith(render_transition_evidence.AUTOGEN_END)
    assert "```text" in section
    assert "https://github.com/<org>/<repo>/actions/runs/<run_id>" in section
    assert section.index("#### Capability: `alpha`") < section.index("#### Capability: `zeta`")
    assert "#### Capability: `empty`" not in section


def test_replace_between_markers_replaces_only_autogen_block() -> None:
    original = "prefix\n" + render_transition_evidence.AUTOGEN_BEGIN + "\nold\n" + render_transition_evidence.AUTOGEN_END + "\nsuffix\n"
    replacement = render_transition_evidence.AUTOGEN_BEGIN + "\nnew\n" + render_transition_evidence.AUTOGEN_END

    updated = render_transition_evidence._replace_between_markers(original, replacement)

    assert updated == "prefix\n" + replacement + "\nsuffix\n"


def test_check_pr_template_autogen_section_returns_zero_when_current(monkeypatch, tmp_path) -> None:
    manifest_path = tmp_path / "dod_manifest.json"
    template_path = tmp_path / "pull_request_template.md"

    manifest = {"capabilities": [{"id": "cap_a", "pytest_commands": ["pytest tests/test_alpha.py"]}]}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    template_path.write_text(render_transition_evidence._render_pr_template_autogen_section(manifest), encoding="utf-8")

    monkeypatch.setattr(render_transition_evidence, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(render_transition_evidence, "PR_TEMPLATE_PATH", template_path)

    assert render_transition_evidence.check_pr_template_autogen_section() == 0


def test_check_pr_template_autogen_section_returns_one_when_stale(monkeypatch, tmp_path) -> None:
    manifest_path = tmp_path / "dod_manifest.json"
    template_path = tmp_path / "pull_request_template.md"

    manifest = {"capabilities": [{"id": "cap_a", "pytest_commands": ["pytest tests/test_alpha.py"]}]}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    template_path.write_text(
        "\n".join(
            [
                render_transition_evidence.AUTOGEN_BEGIN,
                "```text",
                "# stale",
                "```",
                render_transition_evidence.AUTOGEN_END,
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(render_transition_evidence, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(render_transition_evidence, "PR_TEMPLATE_PATH", template_path)

    assert render_transition_evidence.check_pr_template_autogen_section() == 1


def test_main_emits_deterministic_block_for_same_base_and_head(monkeypatch, capsys) -> None:
    manifest = {
        "capabilities": [
            {"id": "cap_a", "status": "in_progress", "pytest_commands": ["pytest tests/test_alpha.py"]},
            {"id": "cap_b", "status": "done", "pytest_commands": ["pytest tests/test_beta.py"]},
        ]
    }

    def fake_check_output(cmd: list[str], text: bool = True) -> str:
        assert text is True
        assert cmd[:2] == ["git", "show"]
        assert cmd[2].endswith(":docs/dod_manifest.json")
        return json.dumps(manifest)

    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    monkeypatch.setattr("sys.argv", ["render_transition_evidence.py", "--base", "abc123", "--head", "abc123"])
    assert render_transition_evidence.main() == 0
    first = capsys.readouterr().out

    monkeypatch.setattr("sys.argv", ["render_transition_evidence.py", "--base", "abc123", "--head", "abc123"])
    assert render_transition_evidence.main() == 0
    second = capsys.readouterr().out

    assert first == second
