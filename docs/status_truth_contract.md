# Status Truth Contract

## Canonical source-of-truth

The **only authoritative input** for capability state, objective status, milestone status, and sprint status is:

- `docs/dod_manifest.json`

Status tooling (`make status`, `make status-json`, `make status-check`, and `make status-sync-check`) must compute status from this manifest only.

## Mode semantics for `make status`

`make status` output must render exactly one explicit mode banner:

- `Offline deterministic mode` — default mode; computed only from canonical repository files.
- `CI-resolved mode` — only when canonical CI evidence links are available and a gate resolves to `pass` or `fail` from that linked evidence.

When canonical CI evidence is absent or unresolved, deterministic fallback behavior is required:

- Never infer `pass`/`fail` from missing CI evidence.
- Render unresolved CI as `unknown` or `CI not resolved offline`.
- `ready` may be emitted only as a manifest readiness signal, not as inferred CI execution outcome.

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
