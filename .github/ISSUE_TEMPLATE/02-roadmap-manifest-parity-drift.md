---
name: ROADMAP and DoD manifest parity drift
description: Track and resolve mismatch between ROADMAP and docs/dod_manifest.json to restore governance parity.
title: "governance: fix ROADMAP ↔ docs/dod_manifest.json parity drift"
labels: ["governance", "docs", "milestone-gate"]
assignees: []
---

## Problem statement

A governance/parity check reported mismatch between `ROADMAP.md` and `docs/dod_manifest.json`.

## Canonical policy decision

- [ ] Confirm canonical source of truth for capability status (`docs/dod_manifest.json` expected).
- [ ] Document synchronization direction and update process.

## Acceptance criteria

- [ ] `ROADMAP.md` and `docs/dod_manifest.json` are synchronized for capability status/sections.
- [ ] CI parity validation fails on future drift (existing checker repaired/extended as needed).
- [ ] Update workflow docs describing how contributors keep these artifacts aligned.
- [ ] Add evidence from a green CI run including parity-related tests/checks.

## Validation commands

```bash
python .github/scripts/validate_milestone_docs.py
pytest tests/test_validate_milestone_docs.py
```
