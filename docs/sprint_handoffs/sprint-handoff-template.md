# Sprint <n> handoff

## Exit criteria pass/fail matrix

| Exit criterion | Status (`pass`/`fail`) | Evidence |
| --- | --- | --- |
| <criterion tied to sprint objective> | pass | <link or artifact> |

## Open risk register with owners/dates

| Risk | Owner | Target resolution date (YYYY-MM-DD) | Mitigation/next step |
| --- | --- | --- | --- |
| <active risk> | <owner> | 2026-01-31 | <mitigation> |

## Next-sprint preload mapped to capability IDs

| Capability ID | Preload objective | Dependency notes |
| --- | --- | --- |
| `capability_id_from_docs/dod_manifest.json` | <objective> | <dependency notes> |


## Workflow quality KPI trend deltas

| KPI | Previous window | Current window | Delta | Evidence |
| --- | --- | --- | --- | --- |
| Median PR CI duration | <minutes> | <minutes> | <+/- minutes and %> | <query/report link> |
| Duplicate-test execution rate | <percent> | <percent> | <+/- percent> | <query/report link> |
| Flaky-check incidence | <percent> | <percent> | <+/- percent> | <query/report link> |
| Bootstrap failure rate | <percent> | <percent> | <+/- percent> | <query/report link> |

## Completed workflow-quality actions

| Action | Source (monthly review / incident / debt budget) | Owner | Status (`done` required at sprint close) | Evidence |
| --- | --- | --- | --- | --- |
| <workflow-quality action> | <source> | <owner> | done | <PR / run / doc link> |

## Quality debt budget updates (if CI/workflow complexity changed)

| Change ID | Added cost | Rollback plan | Owner | Status | Evidence |
| --- | --- | --- | --- | --- | --- |
| <change-id> | <runtime/complexity cost> | <trigger + rollback path> | <owner> | <planned/in_progress/done> | <PR/doc link> |

## Coverage artifact summary

| Artifact | Overall % | Changed-module % | Threshold delta | Evidence |
| --- | --- | --- | --- | --- |
| `coverage.xml` | <overall_coverage_percent> | <changed_module_coverage_percent> | <actual_minus_fail_under> | <CI artifact link or attached report summary> |

_Last regenerated from manifest: 2026-03-01T22:35:00Z (UTC)._
