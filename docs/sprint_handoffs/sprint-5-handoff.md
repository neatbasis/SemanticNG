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
