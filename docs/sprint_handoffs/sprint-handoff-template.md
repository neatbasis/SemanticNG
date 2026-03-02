# Sprint <n> handoff

## Evidence-before-governance update rule

- Governance artifacts are updated only after passing evidence exists and is linked in this handoff.
- Required governance artifacts: `ROADMAP.md`, `docs/dod_manifest.json`, `docs/system_contract_map.md`.
- Evidence links must be attached before status/maturity promotions are recorded.

## Five-sprint objective mapping checklist

- [ ] Sprint 1: one high-impact `capability_invocation_governance` boundary slice with halt semantics + evidence ref.
- [ ] Sprint 2: same path hardened for allow/deny/failure edge cases + normalized audit payload.
- [ ] Sprint 3: minimal usable `repair_aware_projection_evolution` live flow with lineage/replay scenario.
- [ ] Sprint 4: finalize deferred contract fields (`schema_id`, `source`) and deterministic/back-compat coverage.
- [ ] Sprint 5: promote based on evidence, then refresh manifest/contract-map/roadmap.

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

## Coverage artifact summary

| Artifact | Overall % | Changed-module % | Threshold delta | Evidence |
| --- | --- | --- | --- | --- |
| `coverage.xml` | <overall_coverage_percent> | <changed_module_coverage_percent> | <actual_minus_fail_under> | <CI artifact link or attached report summary> |

_Last regenerated from manifest: 2026-03-01T00:00:00Z (UTC)._
