# Integration merge sequencing note

Integration branch: `integration/pr-conflict-resolution`

## Conflict-resolution merge order (by substrate dependency)

1. **#21** — Normalized invariant audit surface (foundational substrate).
2. **#40** — HITL contracts / engine hooks that build on core gate behavior from #21.
3. **#89** — Replay analytics determinism + docs maturity updates, after core behavior stabilizes.
4. **#73** — Promotion rubric/template governance checks, after analytics/docs baseline is aligned.
5. **#43** — Demo runner/scenario packs, merged last due to lowest substrate coupling.

## Rebase-before-merge workflow

To reduce repeated conflict churn, rebase each PR branch onto `integration/pr-conflict-resolution` immediately before merging:

```bash
git checkout <pr-branch>
git rebase integration/pr-conflict-resolution
git checkout integration/pr-conflict-resolution
git merge --no-ff <pr-branch>
```

Apply this workflow in the order above for PRs #21, #40, #89, #73, then #43.

## Temporary merge freeze scope (stabilization window)

Apply a short merge freeze on directly touched conflict-prone files while the integration branch is stabilized:

- `src/state_renormalization/engine.py`
- `src/state_renormalization/contracts.py`
- Governance docs in `docs/` (especially `docs/release_checklist.md`, `docs/dod_manifest.json`, and `docs/system_contract_map.md`).

During this freeze, avoid parallel merges against these paths; route all updates through `integration/pr-conflict-resolution` in the ordered sequence below.

## Serial landing protocol (no parallel merges)

Land the merged stack strictly in the defined order and do fast follow-up rebases between each step:

1. Rebase the next branch onto the latest `integration/pr-conflict-resolution` head.
2. Merge only that single branch.
3. Immediately rebase the next branch after the merge completes.

Do not run concurrent merges for these PRs while freeze is active.

## Required post-merge validation gate (after every merge)

Before advancing to the next PR in sequence, rerun both:

1. Conflict-prone suites (prediction contracts/gates, HITL protocol, replay/projection determinism).
2. Governance validation (`tests/test_validate_milestone_docs.py` and `.github/scripts/validate_milestone_docs.py`).

If either validation group fails, stop sequencing, fix forward on integration, and rerun before continuing.

## Superseded PR closure policy

When a PR is superseded by integration resolution, close it with an explicit `merged-via-integration` note that includes:

- Link to the integration PR/merge commit that preserved behavior.
- Commit SHA(s) containing preserved changes.
- Short list of preserved features/contracts retained.

