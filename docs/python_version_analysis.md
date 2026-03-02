# Python Version Analysis

This document summarizes the Python version policy defined by the repository and the Python version currently active in this execution environment.

## Project-declared Python version policy

- Packaging metadata declares `requires-python = ">=3.10"` in `pyproject.toml`.
- Static-analysis/tooling targets Python 3.10:
  - Ruff `target-version = "py310"`.
  - Mypy `python_version = "3.10"`.
- The README advertises `Python **3.10+**` for contributors.
- CI shared setup (`.github/actions/python-test-setup/action.yml`) defaults to Python `3.10`.
- Weekly parity workflow also pins Python `3.10` for cold-start audits.

## Environment Python version (current runtime)

From local runtime inspection (`python --version`, `python -c ...`, and `.github/scripts/print_env_provenance.py`):

- Active interpreter: CPython 3.11.14
- Executable path: `/root/.pyenv/versions/3.11.14/bin/python`

## Compatibility interpretation

- The environment version (3.11.14) satisfies the project minimum (`>=3.10`).
- However, the repository’s canonical baseline is Python 3.10 (CI defaults + type/lint target config), so the strongest compatibility signal comes from testing against 3.10.
- Running in 3.11 is valid for development and smoke checks, but if version-sensitive behavior appears, reproduce under 3.10 to match CI baseline.
