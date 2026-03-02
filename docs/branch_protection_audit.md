# Branch protection drift audit

This repository treats the following checks as **critical** for both direct PR merges and merge queue entries:

- `Quality Guardrails / no-regression-budget`
- `Quality Guardrails / baseline-lint-type`
- `Quality Guardrails / baseline-test-cov`
- `Quality Guardrails / full-type-surface`
- `State Renormalization Milestone Gate / baseline-quality`
- `State Renormalization Milestone Gate / milestone-governance`

These checks are derived from workflow YAML (`.github/workflows/quality-guardrails.yml` and `.github/workflows/state-renorm-milestone-gate.yml`) by `.github/scripts/audit_branch_protection.py`.

## Automated enforcement

- CI workflow: `.github/workflows/branch-protection-audit.yml`
- Cadence: weekly (`cron: 17 4 * * 1`) and manual dispatch.
- Behavior: fails with a diff of missing/extra required checks when branch protection or rulesets drift from the expected critical set.

## Required token

`GITHUB_TOKEN` may be insufficient to read branch protection and ruleset details in some org configurations.
Set `BRANCH_PROTECTION_AUDIT_TOKEN` with repository administration read access when needed.

## Owner and escalation path

- **Primary owner**: Repository maintainers owning release governance and CI policy.
- **First escalation**: Open an issue tagged `governance` and assign CODEOWNERS for `.github/workflows/**` and `.github/scripts/**`.
- **Urgent escalation** (audit red on default branch): page the release manager/on-call maintainer and immediately restore required checks in both branch protection and merge queue rulesets.

## Manual run

```bash
GH_TOKEN=<token> GITHUB_REPOSITORY=<owner/repo> \
  python .github/scripts/audit_branch_protection.py --branch main
```

## `main` required-check enforcement

`main` branch protection must keep both `Quality Guardrails / baseline-lint-type` and `Quality Guardrails / full-type-surface` as required checks at all times (no optional downgrade).

Canonical required-check policy and temporary exception handling live in `docs/process/quality-gate-policy.md`.

