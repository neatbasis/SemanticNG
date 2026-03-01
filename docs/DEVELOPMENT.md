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

## Local CI-parity preflight

Run these commands in order before every commit/push:

```bash
pre-commit run --all-files
pytest
mypy --config-file=pyproject.toml src tests
```

If `pre-commit` reformats files, stage and rerun until clean:

```bash
git add -A
pre-commit run --all-files
```

## One-command option

`make qa-local` is the repository CI-parity command. It runs hook parity checks, tests, and full-surface mypy.

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
