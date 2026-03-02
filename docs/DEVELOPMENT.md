# Development quickstart (fresh clone to CI parity)

## One-time setup

```bash
git clone <repo>
cd SemanticNG

python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[test]"
pre-commit install
```

## Local quality scopes

### Required pre-commit scope (Tier 1 strict)

Run this before every commit/push:

```bash
pre-commit run --all-files
```

Tier 1 mypy scope is intentionally narrow and enforced by the hook:

- `[tool.mypy].files = ["src/state_renormalization", "src/core"]`
- Hook args: `args: ["--config-file=pyproject.toml", "src/state_renormalization", "src/core"]`

If `pre-commit` reformats files, stage and rerun until clean:

```bash
git add -A
pre-commit run --all-files
```

### Required pre-push gate (strict, no bypass)

**Policy: no push unless the pre-push gate passes.**

Run this before every push (or rely on the installed `pre-push` hook):

```bash
pre-commit run --hook-stage pre-push
```

The pre-push gate must include all of the following checks:

- `ruff` with `--fix`
- `mypy --config-file=pyproject.toml src/state_renormalization src/core`
- Fast deterministic pytest smoke subset (`pytest-quick`)

### Full-surface optional / CI scope (Tier 2 extended)

Use this for full local confidence and CI parity coverage:

```bash
pytest
mypy --config-file=pyproject.toml src tests
```

### Contract-sensitive test typing profile (Tier 2a focused)

Before full strictness on all tests, use the focused profile for engine/contracts/adapters tests:

```bash
mypy --config-file=pyproject.toml tests/test_engine_*.py tests/test_contracts_*.py tests/test_capability_adapter_*.py tests/test_ask_outbox_contracts.py tests/test_predictions_contracts_and_gates.py
```

Pytest markers are auto-assigned in collection, so you can also run:

```bash
pytest -m contract_sensitive
```

`make qa-local` remains the one-command CI-parity option (parity checks + tests + Tier 2 mypy):

```bash
make qa-local
```

## CI failure triage

For local triage parity with CI-style pre-commit failures, run:

```bash
python .github/scripts/classify_precommit_failures.py --log precommit.log
```

## Automated dependency update policy

Repository dependency update automation is defined in `.github/dependabot.yml` and follows governance defaults from release and quality-gate policy.

### Cadence and grouping

- Weekly update window: **Monday 09:00 UTC**.
- Covered ecosystems:
  - GitHub Actions dependencies from `.github/workflows/**` and `.github/actions/**`.
  - Python dependencies resolved from repository `pip` manifests (`pyproject.toml`, `requirements.txt`).
- Grouped PR policy:
  - `dev-test-tooling`: `ruff`, `mypy`, `pytest`, `pre-commit`, and related helper packages (for example `pytest-*`, `types-*`).
  - `runtime-dependencies`: all other Python runtime packages.

### Merge expectations

- Dependabot PRs are labeled for governance routing (`dependencies` + ecosystem-specific labels + `governance`).
- Default reviewer routing follows repository governance ownership expectations (maintainer review for CI/governance impact and quality-gate owner acknowledgement when tooling behavior changes).
- Merge only after required checks pass (at minimum `pre-commit` parity, `pytest`, and applicable `mypy` scope when dependency surface impacts typing).

### Failed dependency PR triage

When an automated dependency PR fails:

1. Classify failure source:
   - CI/config breakage (workflow/action changes).
   - Runtime/test regression (pytest failures).
   - Static analysis/type drift (mypy/ruff/pre-commit failures).
2. Apply the smallest safe remediation in the PR branch:
   - Pin/exclude problematic transitive version.
   - Split group impact by temporarily narrowing update scope.
   - Add upstream issue link when blocked externally.
3. Re-run local parity checks before merge decision:
   - `pre-commit run --all-files`
   - `pytest`
   - `mypy --config-file=pyproject.toml src tests` (or Tier 2a focused scope for contract-boundary drift triage)
4. If not fixable within the update window, close/snooze with rationale and open a tracked follow-up issue that includes blocker owner and retry target date.

### `baseline-lint-type` failing

```bash
pre-commit run --all-files
git add -A
```

### `full-type-surface` failing

```bash
mypy --config-file=pyproject.toml src tests
```

If the failure is isolated to contract boundaries, start with Tier 2a to iterate faster:

```bash
mypy --config-file=pyproject.toml tests/test_engine_*.py tests/test_contracts_*.py tests/test_capability_adapter_*.py tests/test_ask_outbox_contracts.py tests/test_predictions_contracts_and_gates.py
```

Most failures here are typed-test drift (missing annotations, protocol signature mismatch, or stale contract field names).

## Dependency update triage workflow

Dependabot updates are grouped into `dev-test-tooling` and `runtime-dependencies` in `.github/dependabot.yml`.

When a dependency PR fails, open or convert to issue using `.github/ISSUE_TEMPLATE/05-dependabot-failure-triage.md` and classify the failure before merging.

Recommended disposition policy:

- GitHub Actions patch/minor updates: eligible for auto-merge once required checks are green.
- Python `dev-test-tooling` updates (`ruff`, `mypy`, `pytest`, `pre-commit`, typing stubs): require human review because they can alter lint/type gate behavior.
- `runtime-dependencies` updates: require human review plus behavior/regression validation.
