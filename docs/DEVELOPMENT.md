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

### Full-surface optional / CI scope (Tier 2 extended)

Use this for full local confidence and CI parity coverage:

```bash
pytest
mypy --config-file=pyproject.toml src tests
```

`make qa-local` remains the one-command CI-parity option (parity checks + tests + Tier 2 mypy):

```bash
make qa-local
```

## CI failure triage

### `baseline-lint-type` failing

```bash
pre-commit run --all-files
git add -A
```

### `full-type-surface` failing

```bash
mypy --config-file=pyproject.toml src tests
```

Most failures here are typed-test drift (missing annotations, protocol signature mismatch, or stale contract field names).
