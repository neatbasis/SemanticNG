# Release Checklist

Use this checklist before tagging a release.

- [ ] **Milestone gate pass links recorded:** Include links to the latest successful `State Renormalization Milestone Gate` CI run(s) for this release candidate.
- [ ] **Manifest status alignment verified:** `docs/dod_manifest.json` capability statuses match both `ROADMAP.md` milestone placement and the maturity/state reflected in `docs/system_contract_map.md`.
- [ ] **Status transition evidence captured:** For each capability status transition, record the exact milestone `pytest` command(s) from `docs/dod_manifest.json` in the PR body and place a passing `https://...` evidence URL directly below each command string.
- [ ] **PR body evidence is required in addition to manifest fields:** Even when manifest evidence fields are populated (for example `ci_evidence_links`), command/evidence URL pairs must also appear in the PR body for validator pass.
- [ ] **PR-body evidence placement verified:** Evidence must appear in the PR body near each command string (command line followed immediately by its evidence URL).
- [ ] **Manifest evidence limitation acknowledged:** `docs/dod_manifest.json` evidence fields (for example `ci_evidence_links`) are insufficient by themselves for CI validator pass; the same evidence must be present in the PR body in command/evidence pairs.

- [ ] **Local pre-commit guard enabled:** run `git config core.hooksPath .githooks` once per clone so transitioned-capability test commands are executed before commit.
- [ ] **PR evidence block rendered from manifest transitions:** generate exact adjacency-ready command lines with `python .github/scripts/render_transition_evidence.py --base <base_sha> --head <head_sha>` and paste them into the PR body without markdown bullets/backticks.
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
