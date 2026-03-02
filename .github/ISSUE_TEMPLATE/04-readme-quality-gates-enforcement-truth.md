---
name: README quality-gates enforcement truth
description: Ensure README quality-gate claims are mechanically true and auditable.
title: "docs: make README Quality Gates section mechanically true"
labels: ["docs", "governance", "quality-gates"]
assignees: []
---

## Problem statement

README quality statements must match actual repository enforcement.

## Acceptance criteria

- [ ] README includes explicit "How it is enforced" subsection.
- [ ] Subsection references required checks and branch protection/merge-queue enforcement.
- [ ] Language avoids unverifiable claims; each requirement maps to an actual control.
- [ ] CI/docs governance tests pass after README update.

## Verification checklist

- [ ] `README.md` updated with enforcement mapping.
- [ ] Relevant governance docs updated (if needed).
- [ ] Link to green workflow run included in issue resolution.
