# Sprint <n> handoff

## Evidence-before-governance update rule

- Governance artifacts are updated only after passing evidence exists and is linked in this handoff.
- Required governance artifacts: `ROADMAP.md`, `docs/dod_manifest.json`, `docs/system_contract_map.md`.
- Evidence links must be attached before status/maturity promotions are recorded.

## Required status artifacts snapshot

| Artifact field | Required value | Evidence/source |
| --- | --- | --- |
| `latest_directive.id` + `latest_directive.version` | Latest accepted directive record ID/version (for example `DR-2026-001`, `1`). | `docs/directives/*.json` |
| `ci_deterministic_run_name.value` | Deterministic run-name emitted for `qa-ci` stage on this branch/commit. | `python scripts/ci/derive_ci_run_name.py qa-ci --branch <branch>` |
| `last_fail_fast_stop_reason.summary` | Last fail-fast stop summary (or `unknown` with reason when unresolved). | `python scripts/ci/run_stage_checks.py <stage>` logs/artifacts |
| `drift_incidents.*` | Current drift incident count + latest incident summary. | Drift incident tracker / governance notes |
| `drift_incidents.resolution_sla.*` | SLA bounds (triage/fix/waiver business-day targets). | `docs/quality_learning_loop.md` |
| `research_only_dod_usage` | Boolean (`true`/`false`) indicating whether closure relies on research-only DoD usage. | Handoff close rationale |
| `research_only_closure_plan` | Required when `research_only_dod_usage=true`; include owner, due date, and closure path to full DoD. | Follow-up issue/plan link |

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
