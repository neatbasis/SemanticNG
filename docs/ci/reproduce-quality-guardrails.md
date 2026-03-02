# Reproduce quality guardrails locally

Use this checklist to reproduce the same gates used by `.github/workflows/quality-guardrails.yml`.
Run commands from repository root in this exact order.

## 1) Environment setup and baseline lint/type gate

```bash
python --version
python -m pip --version
make qa-baseline
```

`make qa-baseline` runs the same command used in the `baseline-lint-type` CI job:

```bash
make qa-baseline
```

That target expands to:

```bash
python .github/scripts/check_python_support_policy.py
python .github/scripts/check_precommit_parity.py
pre-commit run --all-files
```

## 2) Coverage gate

```bash
make qa-test-cov
```

## 3) Full type surface gate

```bash
make qa-full-type
```

`make qa-full-type` runs the same command used in the `full-type-surface` CI job and executes this mypy invocation:

```bash
mypy --config-file=pyproject.toml src tests
```

## 4) Pre-commit governance selector (targeted capability checks)

The governance selector runs during the local `pre-commit` stage (hook id `precommit-governance-selector`) and computes capability-linked pytest commands for changed paths.

To reproduce it directly, run:

```bash
.github/scripts/run_precommit_governance_checks.py
```

## CI artifacts: where to find them and how to apply them

When `baseline-lint-type` fails in CI, open the run summary and download these artifacts from that job:

- `precommit-log`
- `precommit-classification`
- `precommit-autofix-patch`

Apply and convert the autofix patch to a commit locally:

```bash
git apply precommit_autofix.patch
pre-commit run --all-files
make qa-full-type
git add -A
git commit -m "Apply pre-commit autofixes and satisfy quality guardrails"
```

If `git apply` reports context mismatches, inspect the patch manually and port the changes by hand.

## Troubleshooting matrix

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| `precommit-autofix-patch` artifact exists | Hooks rewrote files and CI failed to force commit of autofixes | Download patch, `git apply precommit_autofix.patch`, re-run `pre-commit run --all-files`, commit changes. |
| mypy import errors (`Cannot find implementation or library stub`) | Missing local dependencies or virtualenv drift | Reinstall project/dev dependencies in the active environment, then rerun `make qa-full-type`. |
| Version mismatch (CI passes/fails differently than local) | Local Python/pip/pre-commit versions differ from CI setup | Compare `python --version` and `python -m pip --version` output to CI logs, then align your toolchain and rerun commands in this doc. |
