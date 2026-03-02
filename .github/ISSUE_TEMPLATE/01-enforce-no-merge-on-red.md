---
name: Enforce no-merge-on-red quality gates
description: Mandatory incident template for red merges; track branch protection and required-check enforcement so merges cannot bypass failing CI.
title: "governance: enforce no-merge-on-red required checks on main"
labels: ["governance", "quality-gates", "ci"]
assignees: []
---

> **Policy:** This is the mandatory incident template whenever a PR is merged while required checks are red/pending.

## Problem statement

Merged PRs can currently land without all relevant checks passing, which creates fail-open behavior against repository quality-gate policy.

## Why this matters

- Violates closed-loop defect prevention expectations.
- Makes README quality policy advisory rather than enforced.
- Allows drift between documented and operational governance.

## Exception ownership and closure

- Exception owner (GitHub handle/team): 
- Target closure date (UTC, YYYY-MM-DD): 

## Acceptance criteria

- [ ] Branch protection on `main` requires `Quality Guardrails`.
- [ ] Branch protection requires `State Renormalization Milestone Gate` (or equivalent scoped requirement for milestone-governed changes).
- [ ] Merges are blocked when required checks are failing or pending.
- [ ] Merge queue is enabled and required checks run on `merge_group` commit.
- [ ] README "Quality Gates" section is verified against actual branch protection settings and quarterly audit evidence is linked.

## Evidence to attach

- Screenshot or exported settings from repository branch protection.
- Example PR showing blocked merge on failing required check.
- Completed/closed date (UTC, YYYY-MM-DD): 
