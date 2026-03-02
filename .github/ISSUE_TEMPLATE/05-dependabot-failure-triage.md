---
name: Dependabot failure triage
description: Triage and resolve failing dependency update PRs using the repository policy playbook.
title: "deps: triage failing Dependabot update"
labels: ["dependencies", "dependabot", "triage"]
assignees: []
---

## Dependabot PR context

- PR link:
- Update group (`dev-test-tooling` or `runtime-dependencies`):
- Dependency/dependencies updated:
- Update type (patch/minor/major):

## Failure classification

- [ ] Toolchain/parity failure (pre-commit, mypy scope, version policy)
- [ ] Test/behavior regression
- [ ] Build/install/import failure
- [ ] Workflow/action failure
- [ ] Other (describe)

## Triage checklist

- [ ] Reproduce locally via canonical commands:

```bash
pre-commit run --all-files
pytest --cov --cov-report=term-missing --cov-report=xml
mypy --config-file=pyproject.toml src tests
```

- [ ] Confirm labels are correct for routing (`dev-test-tooling`, `runtime-dependencies`).
- [ ] Determine disposition:
  - [ ] Fix-forward in PR
  - [ ] Pin/ignore with documented rationale
  - [ ] Split updates into smaller batch
- [ ] Add postmortem note to `docs/DEVELOPMENT.md` triage policy if a new failure mode was discovered.

## Merge policy decision

- [ ] Eligible for auto-merge under repository policy.
- [ ] Requires human review and explicit approval.

## Resolution evidence

- Link to passing workflow run:
- Notes:
