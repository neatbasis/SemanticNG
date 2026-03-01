# Python Version Analysis (3.10 Policy)

## Executive summary

The repository is internally consistent on a **"minimum Python 3.10"** contract, but it is **not enforcing an "exactly Python 3.10" runtime contract**.

This means teams can still run local tooling on Python 3.11+ (as happened in this environment), while CI defaults to 3.10. That can introduce behavior drift and false confidence if 3.11-only behavior slips into development workflows.

## What is aligned today

- `pyproject.toml` sets `requires-python = ">=3.10"`.
- `README.md` documents `- Python **3.10+**`.
- CI shared action (`.github/actions/python-test-setup/action.yml`) defaults to `python-version: '3.10'`.
- Guardrail script (`.github/scripts/check_python_support_policy.py`) verifies pyproject/README/CI-default stay in sync.
- Pre-commit hook environments pin `language_version: python3.10` for `ruff`, `ruff-format`, and `mypy`.

## Hints suggesting policy ambiguity (root-cause analysis)

### 1) Minimum-version contract vs exact-version intent

If the intended policy is "project should use Python 3.10" (exact major.minor), the current contract is too loose:

- `requires-python = ">=3.10"` explicitly allows 3.11, 3.12, etc.
- README uses "3.10+", reinforcing minimum-version semantics.

**Root cause:** packaging metadata and docs were authored around compatibility floor semantics, not runtime standardization semantics.

### 2) Policy checker enforces consistency, not strictness

`check_python_support_policy.py` parses only `>=X.Y` format and derives an expected README line of `Python **X.Y+**`.

**Root cause:** the checker intentionally codifies "minimum-only" policy; it cannot represent or enforce "==3.10.*" style constraints even if that is desired.

### 3) CI uses 3.10 default, but developers can still run other interpreters locally

CI jobs that use the shared setup action inherit default 3.10, and the weekly parity job explicitly sets 3.10. However, nothing prevents local development from using a different interpreter.

**Root cause:** local environment controls are advisory (`README`/docs commands) rather than enforced (`.python-version`, devcontainer pin, or strict preflight interpreter check).

## Environment verification results

- Local interpreter in this run was Python **3.11.14**.
- Python support policy script passed, confirming internal **minimum-3.10** consistency.
- `pydantic` import failed in this environment (`ModuleNotFoundError`).
- Attempting to install project dependencies failed due restricted package index/proxy access (`setuptools>=64` build dependency could not be resolved).

## Recommended remediations (if exact 3.10 is required)

1. Decide policy explicitly:
   - Keep **minimum compatibility** (`>=3.10`) or
   - Move to **runtime standardization** (exact 3.10 for all quality gates and local guidance).
2. If exact 3.10 is intended, update:
   - `README.md` wording from "3.10+" to "3.10.x".
   - Add `.python-version` with `3.10` (or equivalent local pinning mechanism).
   - Extend `check_python_support_policy.py` to validate strict policy mode.
3. Add a lightweight preflight script in `make bootstrap` that fails fast when local interpreter is not 3.10 (if strict mode selected).
4. Keep CI parity checks, but make policy semantics explicit in docs (`docs/dev_toolchain_parity.md` and `docs/DEVELOPMENT.md`).

## Recommendation when keeping minimum-version policy

If the team intentionally wants compatibility across 3.10+:

- Keep existing config as-is,
- but clarify in docs that **CI baseline is 3.10** while local may be newer,
- and require targeted compatibility checks when introducing syntax/features newer than 3.10.
