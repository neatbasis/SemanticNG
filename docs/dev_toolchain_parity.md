# Dev Toolchain Parity Map

This document is the canonical dependency map for the local Python quality toolchain.

It defines:

- Which hooks scan which code paths.
- Which third-party imports must be available to each hook.
- Whether each dependency is sourced from `pyproject.toml` extras or from hook-local
  `additional_dependencies`.

## Python policy baseline

- Project runtime and CI baseline: Python 3.11 (`pyproject.toml` `[project].requires-python`
  and `.github/actions/python-test-setup/action.yml`).
- Hook parity policy: pin hook `language_version` to `python3.11` for tools that execute in an
  isolated pre-commit environment.

## Hook dependency map

| Hook | Scope | Required imports in scanned code paths | Package source |
| --- | --- | --- | --- |
| `mypy` | `[tool.mypy].files = ["src/state_renormalization", "src/core"]`; hook args `args: ["--config-file=pyproject.toml", "src/state_renormalization", "src/core"]` | `pydantic`, `pytest`, `gherkin`, `typing_extensions` | Hook `additional_dependencies` in `.pre-commit-config.yaml` (isolated env) |
| `ruff` | `src`, `tests` (from `[tool.ruff].src`) | None beyond Ruff itself for static analysis | Project tooling dependency from `pyproject.toml` `test` extra (`ruff`) |
| `ruff-format` | `src`, `tests` (from `[tool.ruff].src`) | None beyond Ruff itself for static analysis | Project tooling dependency from `pyproject.toml` `test` extra (`ruff`) |
| `pytest-quick` (local hook) | `tests/test_engine_pending_obligation.py`, `tests/test_invariants.py` | `pytest` | Project tooling dependency from `pyproject.toml` `test` extra (`pytest`) |

## Mypy scope tiers (canonical)

- Tier 1 (strict, required pre-commit): `src/state_renormalization`, `src/core`
- Tier 2 (extended, optional local / CI full-surface): `src`, `tests`

Canonical source: `[tool.semanticng.mypy_tiers]` in `pyproject.toml`.

## Drift controls

- `.github/scripts/check_precommit_parity.py` enforces known parity invariants:
  - `mypy` includes all required third-party dependency declarations for its scan scope.
  - `mypy` additional dependency constraints stay aligned with `pyproject.toml` dependency constraints.
  - `mypy`, `ruff`, and `ruff-format` pin `language_version` to `python3.11`.
  - Workflow Python versions used for parity-sensitive quality jobs stay aligned with the project Python baseline.
- CI runs this parity check before `pre-commit run --all-files`.

## Ownership and review cadence

- **Owner:** `@semanticng/toolchain-parity-maintainers` owns toolchain parity policy, break/fix response, and exception approvals.
- **Cadence:** run a monthly parity hygiene review to:
  - prune stale mypy override allowances,
  - remove obsolete hook `additional_dependencies` exceptions,
  - retire temporary dependency waivers once upstream constraints are stable,
  - confirm scheduled cold-start parity workflow results remain green.
