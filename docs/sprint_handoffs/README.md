# Sprint handoff artifacts

Canonical location: `docs/sprint_handoffs/`.

## Naming

- One sprint handoff file per sprint: `sprint-<n>-handoff.md`
- Start from `sprint-handoff-template.md`.

## Required sections

Every sprint handoff artifact must include:

1. `## Exit criteria pass/fail matrix`
2. `## Open risk register with owners/dates`
3. `## Next-sprint preload mapped to capability IDs`
4. `## Workflow quality KPI trend deltas`
5. `## Completed workflow-quality actions`
6. `## Coverage artifact summary`

The preload section must reference capability IDs that exist in `docs/dod_manifest.json`.

KPI trend section must provide previous/current values and deltas for: median PR CI duration, duplicate-test execution rate, flaky-check incidence, and bootstrap failure rate.

Completed workflow-quality actions section must include actions marked `done` with evidence links at sprint close.

Coverage artifact summaries must include, at minimum:

- Overall coverage percentage (`overall %`)
- Changed-module coverage percentage (`changed-module %`)
- Threshold delta (`actual % - fail_under threshold`)
- Evidence reference (CI artifact link or attached report excerpt)

_Last regenerated from manifest: 2026-03-01T22:50:00Z (UTC)._
