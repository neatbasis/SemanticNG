# Quality Feedback Architecture Scorecard

Date: 2026-03-02

This scorecard maps SemanticNG against 10 meta-patterns of exemplary quality systems, with emphasis on automated lint/type/test gates and CI invariants.

Scoring scale:

- 5 = strong institutionalized pattern
- 3 = partially implemented / inconsistent
- 1 = mostly absent

## Score summary

| # | Pattern | Score | Notes |
| --- | --- | --- | --- |
| 1 | Collapse tool graph | 4/5 | Canonical pre-commit path exists and is used in CI; CI still has additional direct commands by design. |
| 2 | Shift failure left | 4/5 | Ruff autofix + local pre-commit workflow are strong. |
| 3 | Reduce configuration entropy | 4/5 | `pyproject.toml` is canonical for most tooling + parity checker script. |
| 4 | Make good behavior easiest | 4/5 | `make qa-local` and documented quickstart support low-friction compliance. |
| 5 | Enforce invariants at boundaries | 3/5 | Workflow gates are defined, but merged PR evidence shows fail-open operation if branch protection is not strict. |
| 6 | Manage dependency drift | 4/5 | Dependabot is configured with grouped updates and cadence. |
| 7 | Control batch size | 3/5 | Grouped dependency updates and milestone-selected test commands help, but CI breadth remains non-trivial. |
| 8 | Expose signals publicly | 4/5 | README badges + quality section provide visible governance signals. |
| 9 | Baseline freeze / no-new-violations | 3/5 | Policy intent is explicit, enforcement depends on branch protection settings. |
| 10 | Encode architecture boundaries | 5/5 | Strong contract and capability boundary modeling in docs/manifests/tests. |

**Total: 38/50**

## Highest-risk gap: documented fail-fast vs operational fail-open

The most material governance risk is mismatch between documented merge policy and actual enforcement when required checks are not branch-protected.

Action: use `.github/ISSUE_TEMPLATE/01-enforce-no-merge-on-red.md` to track and close this gap.

## Recommended issue intake order

1. Enforce no-merge-on-red required checks.
2. Restore ROADMAP ↔ `docs/dod_manifest.json` parity discipline.
3. Keep policy-surface formatting guardrails strict and readable.
4. Keep README quality statements mechanically true.
5. Operationalize Dependabot failure triage with labels/routing checklist.
