from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "dev" / "verify_precommit_installed.py"


spec = importlib.util.spec_from_file_location("verify_precommit_installed", SCRIPT_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)


def test_resolve_hooks_dir_defaults_to_dot_git_hooks(tmp_path: Path) -> None:
    _init_repo(tmp_path)

    hooks_dir = module._resolve_hooks_dir(tmp_path)

    assert hooks_dir == tmp_path / ".git" / "hooks"


def test_resolve_hooks_dir_uses_custom_relative_core_hooks_path(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    subprocess.run(
        ["git", "config", "core.hooksPath", ".githooks/custom"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    hooks_dir = module._resolve_hooks_dir(tmp_path)

    assert hooks_dir == tmp_path / ".githooks" / "custom"


def test_validate_hook_reports_missing_files_in_custom_hooks_path(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    subprocess.run(
        ["git", "config", "core.hooksPath", ".githooks/custom"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    hooks_dir = module._resolve_hooks_dir(tmp_path)

    missing_pre_commit = module._validate_hook(hooks_dir / "pre-commit")
    missing_pre_push = module._validate_hook(hooks_dir / "pre-push")

    assert missing_pre_commit == f"Missing required hook: {hooks_dir / 'pre-commit'}"
    assert missing_pre_push == f"Missing required hook: {hooks_dir / 'pre-push'}"
