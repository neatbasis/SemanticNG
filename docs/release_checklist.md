# Release Checklist

Use this checklist before tagging a release.

## Canonical contributor workflow expectations

This document is the canonical source for active release/integration workflow expectations.

- Default to standard PR flow with branch protection and required checks enabled.
- Use milestone gate + manifest evidence as merge prerequisites for milestone/maturity changes.
- Treat `docs/integration_notes.md` as historical context only unless its explicit activation criteria are met.

- [ ] **Milestone gate pass links recorded:** Include links to the latest successful `State Renormalization Milestone Gate` CI run(s) for this release candidate.
- [ ] **Manifest is canonical:** Capability status, code paths, and command coverage are updated directly in `docs/dod_manifest.json`.
- [ ] **Status transition commands captured in manifest:** Each transitioned capability has complete `pytest_commands` and synchronized `ci_evidence_links.command` entries in manifest order.
- [ ] **Milestone gate pass links recorded:** CI run links are captured in manifest `ci_evidence_links` and/or release notes as needed (PR-body duplication is optional).


## Governance enforcement requirements

- [ ] **No-regression budget respected:** All `done` capability command packs remain green with zero unapproved failures.
- [ ] **Regression waiver timeboxed:** Any waiver includes owner, rationale, rollback-by date, and mitigation command packs.
- [ ] **Dependency impact statements present:** Every merged PR includes upstream/downstream impact and cross-capability risk statements.
- [ ] **Capability maturity gates enforced:** `planned -> in_progress -> done` transitions are validated by CI entry/exit gate checks.
- [ ] **Documentation freshness SLO met:** Governed docs are within freshness threshold and include current regeneration metadata.
- [ ] **Sprint handoff minimum artifacts attached:** Sprint-close report includes exit table, open-risk register, and next-sprint preload list.

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

## Exceptional integration stabilization controls (reactivation only)

Use these controls only when the activation criteria in `docs/integration_notes.md` are met:

- [ ] **Merge freeze scope explicitly declared:** Conflict-prone files and governance docs in scope are listed in the integration plan.
- [ ] **Stack merged serially in defined order:** Integration merges are landed one-by-one (not in parallel) with immediate follow-up rebases.
- [ ] **Post-merge validation run after each landed PR:** Conflict-prone suites and governance validation pass before moving to the next PR.
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
