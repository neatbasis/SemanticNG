# Status Truth Contract

## Canonical source-of-truth

The **only authoritative input** for capability state, objective status, milestone status, and sprint status is:

- `docs/dod_manifest.json`

Status tooling (`make status`, `make status-json`, `make status-check`, and `make status-sync-check`) must compute status from this manifest only.

## Generated views (non-authoritative)

The following files are generated views and must never be used as authoritative inputs:

- `docs/status/project.json`
- `docs/status/objectives.json`
- `docs/status/milestones.json`
- `docs/status/sprints.json`

Generation entrypoint: `scripts/dev/render_status_from_manifest.py`.

## Narrative-only documents (non-authoritative)

The following docs are narrative context only. They may reference IDs and provide links/evidence but are never parsed as source-of-truth status fields:

- `ROADMAP.md`
- `docs/sprint_plan_5x.md`
- `docs/sprint_handoffs/*.md`

References in roadmap and sprint markdown are link/annotation surfaces only.
