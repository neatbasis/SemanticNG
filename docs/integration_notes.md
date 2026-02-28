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
