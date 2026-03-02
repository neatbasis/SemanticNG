# Contributing

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

## Pre-push quality requirement

Before every push, run the full pre-commit suite from the repository root:

```bash
pre-commit run --all-files
```

If any hook rewrites files, you must stage and commit those changes before pushing.

Recommended local sequence:

```bash
pre-commit run --all-files
git add -A
git commit -m "Apply pre-commit fixes"
```

If CI uploads a `precommit-autofix-patch` artifact, you can apply it locally with:

```bash
scripts/ci/apply_precommit_patch.sh /path/to/precommit_autofix.patch
```
