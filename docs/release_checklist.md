# Release Checklist

Use this checklist before tagging a release.

- [ ] **Milestone gate pass links recorded:** Include links to the latest successful `State Renormalization Milestone Gate` CI run(s) for this release candidate.
- [ ] **Manifest is canonical:** Capability status, code paths, and command coverage are updated directly in `docs/dod_manifest.json`.
- [ ] **Status transition commands captured in manifest:** Each transitioned capability has complete `pytest_commands` and synchronized `ci_evidence_links.command` entries in manifest order.
- [ ] **Milestone gate pass links recorded:** CI run links are captured in manifest `ci_evidence_links` and/or release notes as needed (PR-body duplication is optional).

## Copy/paste evidence block (validator-compatible)

Generate the PR-template block from `docs/dod_manifest.json` instead of maintaining command examples here:

```bash
python .github/scripts/render_transition_evidence.py --emit-pr-template-autogen
```

Use the generated capability sections where needed (PR notes, release notes, or docs). URLs default to the current CI run URL when generated in GitHub Actions.

## Merge expectations for milestone and maturity PRs

Do not merge milestone or maturity update PRs until all conditions are met:

1. `State Renormalization Milestone Gate` CI is passing on the PR head SHA.
2. `docs/dod_manifest.json` contains the canonical command/evidence mapping for transitioned capabilities.
3. Any derived docs are regenerated from the manifest when required.

## Integration branch stabilization controls (temporary)

- [ ] **Merge freeze applied for touched files:** `src/state_renormalization/engine.py`, `src/state_renormalization/contracts.py`, and governance docs are frozen for direct parallel merges during stabilization.
- [ ] **Stack merged serially in defined order:** Integration merges were landed one-by-one (not in parallel) with immediate follow-up rebases between merges.
- [ ] **Post-merge validation run after each landed PR:** Conflict-prone suites and governance validation both passed before moving to the next PR.
- [ ] **Superseded PRs closed with `merged-via-integration` notes:** Every superseded PR includes links to preserving integration commits and a feature-retention summary.

## Integration PR feature-retention checklist

When preparing an integration PR that reconciles multiple incoming branches, include a feature-retention section in the PR body that enumerates each still-open PR and the exact preserved behavior(s).

Use this template:

```markdown
## Feature-retention checklist

- [ ] PR #<number> — <short title>
  - Preserved behavior: <specific behavior retained after reconciliation>
  - Validation command: `<exact command>`
  - Evidence: <https://... or artifact://...>
- [ ] PR #<number> — <short title>
  - Preserved behavior: <specific behavior retained after reconciliation>
  - Validation command: `<exact command>`
  - Evidence: <https://... or artifact://...>
```

If conflict reconciliation drops or defers any behavior, do not merge immediately: open follow-up patch PR(s) in the same integration cycle and link them under the affected checklist entry.
