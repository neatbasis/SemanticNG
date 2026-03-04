from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_STAGE_CHECKS_PATH = ROOT / "scripts" / "ci" / "run_stage_checks.py"

SPEC = importlib.util.spec_from_file_location("run_stage_checks_preflight", RUN_STAGE_CHECKS_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _target_recipe(makefile: str, target: str) -> str:
    match = re.search(rf"^{re.escape(target)}:\n\t(.+)$", makefile, re.MULTILINE)
    assert match, f"Missing target recipe for {target}"
    return match.group(1)


def test_preflight_canonical_and_qa_ci_use_same_stage_manifest_entrypoint() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    qa_ci_recipe = _target_recipe(makefile, "qa-ci")
    preflight_recipe = _target_recipe(makefile, "preflight-canonical")

    assert qa_ci_recipe == "python scripts/ci/run_stage_checks.py qa-ci"
    assert preflight_recipe == "python scripts/ci/run_stage_checks.py qa-ci --mode local"


def test_preflight_canonical_stage_order_matches_manifest() -> None:
    manifest = json.loads((ROOT / "docs/process/quality_stage_commands.json").read_text(encoding="utf-8"))
    expected_order = [stage["id"] for stage in manifest["stages"]["qa-ci"]["ordered_stages"]]

    loaded = MODULE._load_stages()
    actual_order = [stage.id for stage in loaded["qa-ci"].ordered_stages]

    assert actual_order == expected_order


def test_mode_local_disables_ci_env_auto_full_stage(monkeypatch, capsys) -> None:
    fake_stages = {
        "qa-commit": MODULE.StageSpec(
            ordered_stages=(
                MODULE.OrderedStageSpec(
                    id="qa-commit-local-gates",
                    stop_on_fail=True,
                    commands=(
                        MODULE.CommandSpec(
                            command="runs-only-on-src",
                            timeout_seconds=1,
                            run_if_paths=("src/**/*.py",),
                        ),
                    ),
                ),
            ),
            commands=(
                MODULE.CommandSpec(
                    command="runs-only-on-src",
                    timeout_seconds=1,
                    run_if_paths=("src/**/*.py",),
                ),
            ),
        )
    }

    monkeypatch.setattr(MODULE, "_load_stages", lambda: fake_stages)
    monkeypatch.setattr(MODULE, "_staged_files", lambda: ("docs/DEVELOPMENT.md",))
    monkeypatch.setattr(MODULE, "_run_command", lambda spec: (_ for _ in ()).throw(AssertionError("should not run")))
    monkeypatch.setenv("CI", "1")
    monkeypatch.setattr(sys, "argv", ["run_stage_checks.py", "qa-commit", "--mode", "local"])

    result = MODULE.main()
    output = capsys.readouterr().out

    assert result == 0
    assert "Stage mode: staged-path filtered" in output
    assert "No commands matched changed paths; stage passed without running commands." in output
