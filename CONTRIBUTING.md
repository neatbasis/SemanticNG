# Contributing

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
