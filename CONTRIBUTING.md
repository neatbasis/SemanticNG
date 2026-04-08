# Contributing

## Documentation index

Before making governance, architecture, or process doc updates, start from [`docs/README.md`](docs/README.md), the single repository documentation entrypoint.

## Mandatory hook installation

Local development requires both Git hooks installed via `pre-commit` (`pre-commit` and `pre-push`).

```bash
make bootstrap
```

This runs:

```bash
pre-commit install --hook-type pre-commit --hook-type pre-push
pre-commit install-hooks
python scripts/dev/verify_precommit_installed.py
```

If verification fails, follow the remediation text printed by the verifier and rerun `make bootstrap`.

## Commit-time smoke-test policy

The `pre-commit` hook path now includes a deterministic pytest smoke subset via `make qa-commit`.
This ensures basic runtime regressions are surfaced before commit creation.

Run manually when needed:

```bash
make qa-commit
```

## Pre-push quality requirement

Before every push, run the enforced push gate:

```bash
make qa-push
```

Run promotion governance checks whenever semantic-boundary files are staged:

```bash
make promotion-checks
```

If any hook/check rewrites files, stage and rerun until clean.

Recommended local sequence before committing:

```bash
git status --short --branch
make verify-dev-setup
make qa-commit
make qa-push
make promotion-checks
```

If CI uploads a `precommit-autofix-patch` artifact, you can apply it locally with:

```bash
scripts/ci/apply_precommit_patch.sh /path/to/precommit_autofix.patch
```
