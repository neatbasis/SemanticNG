# Sprint handoff artifacts

Canonical location: `docs/sprint_handoffs/`.

Additional planning artifact:

- `mypy-debt-5-sprint-timeline.md` — explicit 5-sprint exit criteria for mypy suppression burn-down governance.

## Naming

- One sprint handoff file per sprint: `sprint-<n>-handoff.md`
- Start from `sprint-handoff-template.md`.

## Required sections

Every sprint handoff artifact must include:

1. `## Exit criteria pass/fail matrix`
2. `## Open risk register with owners/dates`
3. `## Next-sprint preload mapped to capability IDs`
4. `## Coverage artifact summary`

The preload section must reference capability IDs that exist in `docs/dod_manifest.json`.

Coverage artifact summaries must include, at minimum:

- Overall coverage percentage (`overall %`)
- Changed-module coverage percentage (`changed-module %`)
- Threshold delta (`actual % - fail_under threshold`)
- Evidence reference (CI artifact link or attached report excerpt)

_Last regenerated from manifest: 2026-03-01T00:00:00Z (UTC)._

## Governance update ordering (mandatory)

- Governance artifacts are updated only after passing evidence exists and is linked from the sprint handoff.
- Update order is evidence first, then synchronized changes to `ROADMAP.md`, `docs/dod_manifest.json`, and `docs/system_contract_map.md`.

## Five-sprint objective anchors

Handoffs and preload plans should map scope/evidence to these sprint objectives:

1. Sprint 1: one high-impact `capability_invocation_governance` boundary slice with halt semantics + evidence ref.
2. Sprint 2: same path hardened for allow/deny/failure edge cases + normalized audit payload.
3. Sprint 3: minimal usable `repair_aware_projection_evolution` live flow with lineage/replay scenario.
4. Sprint 4: finalize deferred contract fields (`schema_id`, `source`) and deterministic/back-compat coverage.
5. Sprint 5: promote based on evidence, then refresh manifest/contract-map/roadmap.
