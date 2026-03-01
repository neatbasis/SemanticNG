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
4. `## Coverage artifact summary`

The preload section must reference capability IDs that exist in `docs/dod_manifest.json`.

Coverage artifact summaries must include, at minimum:

- Overall coverage percentage (`overall %`)
- Changed-module coverage percentage (`changed-module %`)
- Threshold delta (`actual % - fail_under threshold`)
- Evidence reference (CI artifact link or attached report excerpt)
