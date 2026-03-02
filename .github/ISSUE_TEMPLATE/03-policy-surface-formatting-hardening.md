---
name: Policy surface formatting hardening
description: Restore and enforce human-readable formatting for key governance/config files.
title: "governance: harden formatting for policy-surface files"
labels: ["governance", "tooling", "docs", "pre-commit"]
assignees: []
---

## Problem statement

Policy/config files must remain easy to review and diff. Dense or single-line formatting is high-risk for governance drift.

## In-scope files

- [ ] `README.md`
- [ ] `.pre-commit-config.yaml`
- [ ] `.github/dependabot.yml`
- [ ] `docs/DEVELOPMENT.md`
- [ ] `pyproject.toml` (recommended)

## Acceptance criteria

- [ ] Files above are normalized to readable multiline structure.
- [ ] Formatting checks are automated in pre-commit and CI (Markdown/YAML/TOML coverage).
- [ ] CONTRIBUTING/development docs include one-command formatting guidance.
- [ ] At least one regression test/check demonstrates formatting guardrail is active.

## Candidate implementation notes

- Keep pre-commit hooks as the canonical invocation path.
- Prefer a single-source formatter policy over ad-hoc scripts.
