# Release Checklist

Use this checklist before tagging a release.

- [ ] **Milestone gate pass links recorded:** Include links to the latest successful `State Renormalization Milestone Gate` CI run(s) for this release candidate.
- [ ] **Manifest status alignment verified:** `docs/dod_manifest.json` capability statuses match both `ROADMAP.md` milestone placement and the maturity/state reflected in `docs/system_contract_map.md`.
- [ ] **Status transition evidence captured:** For each capability status transition, record the exact milestone `pytest` command(s) from `docs/dod_manifest.json` and attach passing evidence links.
- [ ] **Maturity changelog updates captured:** Every maturity promotion/demotion in `docs/system_contract_map.md` has a dated changelog entry and corresponding CI evidence link.

## Merge expectations for milestone and maturity PRs

Do not merge milestone or maturity update PRs until all conditions are met:

1. `State Renormalization Milestone Gate` CI is passing on the PR head SHA.
2. PR checklist includes command-by-command evidence links for all status transitions.
3. `ROADMAP.md`, `docs/dod_manifest.json`, and `docs/system_contract_map.md` remain internally consistent after the update.
