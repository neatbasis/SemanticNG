# Release Checklist

Use this checklist before tagging a release.

- [ ] **Milestone gate pass links recorded:** Include links to the latest successful `State Renormalization Milestone Gate` CI run(s) for this release candidate.
- [ ] **Manifest status alignment verified:** `docs/dod_manifest.json` capability statuses match both `ROADMAP.md` milestone placement and the maturity/state reflected in `docs/system_contract_map.md`.
- [ ] **Status transition evidence captured:** For each capability status transition, record the exact milestone `pytest` command(s) from `docs/dod_manifest.json` in the PR body and place a passing `https://...` evidence link directly below each command string.
- [ ] **PR body evidence is required in addition to manifest fields:** Even when manifest evidence fields are populated (for example `ci_evidence_links`), command/evidence pairs must also appear in the PR body for validator pass.
- [ ] **PR-body evidence placement verified:** Evidence must appear in the PR body near each command string (command line followed immediately by its evidence URL).
- [ ] **Manifest evidence limitation acknowledged:** `docs/dod_manifest.json` evidence fields (for example `ci_evidence_links`) are insufficient by themselves for CI validator pass; the same evidence must be present in the PR body in command/evidence pairs.
- [ ] **Maturity changelog updates captured:** Every maturity promotion/demotion in `docs/system_contract_map.md` has a dated changelog entry and corresponding CI evidence link.

## Copy/paste evidence block (validator-compatible)

Use this exact shape in the PR body for every status transition command:

```text
pytest tests/milestones/test_alpha.py -k gate
https://github.com/<org>/<repo>/actions/runs/123456789

pytest tests/milestones/test_beta.py -k readiness
https://github.com/<org>/<repo>/actions/runs/987654321
```

## Merge expectations for milestone and maturity PRs

Do not merge milestone or maturity update PRs until all conditions are met:

1. `State Renormalization Milestone Gate` CI is passing on the PR head SHA.
2. PR checklist includes command-by-command evidence links for all status transitions.
3. `ROADMAP.md`, `docs/dod_manifest.json`, and `docs/system_contract_map.md` remain internally consistent after the update.
