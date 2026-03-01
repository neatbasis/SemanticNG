# Sprint 5 handoff

## Exit criteria pass/fail matrix

| Exit criterion | Status (`pass`/`fail`) | Evidence |
| --- | --- | --- |
| Governance + milestone checks continue passing after sprint close. | pass | `pytest tests/test_validate_milestone_docs.py tests/test_governance_pr_evidence_validator.py` |
| Sprint handoff artifact format validation enforces mandatory sections and capability mapping. | pass | `pytest tests/test_sprint_handoff_validation.py` |

## Open risk register with owners/dates

| Risk | Owner | Target resolution date (YYYY-MM-DD) | Mitigation/next step |
| --- | --- | --- | --- |
| Sprint-close metadata drift if future handoffs omit required tables. | Repo maintainers | 2026-03-31 | Keep CI validation on governance + sprint-close PRs and review failures before merge. |

## Next-sprint preload mapped to capability IDs

| Capability ID | Preload objective | Dependency notes |
| --- | --- | --- |
| `capability_invocation_governance` | Reconfirm no-regression command packs and evidence links remain current after handoff gating rollout. | Depends on milestone governance workflow and no-regression policy checks. |
| `repair_aware_projection_evolution` | Prepare implementation sequencing and test scaffolding before moving status. | Depends on replay/invariant suites and policy guard stability. |


## Workflow quality KPI trend deltas

| KPI | Previous window | Current window | Delta | Evidence |
| --- | --- | --- | --- | --- |
| Median PR CI duration | 19.5 min | 18.2 min | -1.3 min (-6.7%) | workflow analytics board sprint-5 |
| Duplicate-test execution rate | 9.0% | 6.0% | -3.0 pts | workflow analytics board sprint-5 |
| Flaky-check incidence | 3.2% | 2.1% | -1.1 pts | workflow analytics board sprint-5 |
| Bootstrap failure rate | 1.8% | 0.9% | -0.9 pts | workflow analytics board sprint-5 |

## Completed workflow-quality actions

| Action | Source (monthly review / incident / debt budget) | Owner | Status (`done` required at sprint close) | Evidence |
| --- | --- | --- | --- | --- |
| Added workflow command-policy drift report and CI enforcement step. | monthly review | Repo maintainers | done | `.github/scripts/workflow_policy_drift_report.py`; `.github/workflows/quality-guardrails.yml` |
| Added sprint-close KPI/delta evidence section and quality debt budget tracking template. | debt budget | Repo maintainers | done | `docs/sprint_handoffs/sprint-handoff-template.md`; `docs/release_checklist.md` |

## Quality debt budget updates (if CI/workflow complexity changed)

| Change ID | Added cost | Rollback plan | Owner | Status | Evidence |
| --- | --- | --- | --- | --- | --- |
| wf-drift-report-2026-03 | +0.2 min/run | Remove drift-report step from workflows if CI median duration regresses >10% for 2 weeks and file follow-up optimization PR in same sprint. | Repo maintainers | planned | `python .github/scripts/workflow_policy_drift_report.py --summary` |

_Last regenerated from manifest: 2026-03-01T22:45:00Z (UTC)._
