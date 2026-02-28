# Release Checklist

Use this checklist before tagging a release.

- [ ] **Milestone gate pass links recorded:** Include links to the latest successful `State Renormalization Milestone Gate` CI run(s) for this release candidate.
- [ ] **Manifest status alignment verified:** `docs/dod_manifest.json` capability statuses match both `ROADMAP.md` milestone placement and the maturity/state reflected in `docs/system_contract_map.md`.
- [ ] **Status transition evidence captured:** For each capability status transition, record the exact milestone `pytest` command(s) from `docs/dod_manifest.json` and attach passing evidence links.
