# DR-2026-001: Milestone source-of-truth acceptance criteria

## Metadata

- **Status:** accepted
- **Date:** 2026-03-01
- **Owners:** repo-maintainers
- **CI policy:** blocking
- **Supersedes:** none

## Context

Sprint 5 handoff captured milestone exit criteria that must remain canonical and auditable: (1) governance + milestone checks continue passing after sprint close and (2) sprint handoff artifact format validation enforces mandatory sections and capability mapping.

## Decision

Establish this directive record as the source of truth for milestone acceptance criteria and require schema-backed decision record validation as part of relevant governance PR evidence.

## Consequences

Milestone governance PRs must preserve both acceptance criteria and include decision record schema validation evidence so source-of-truth directives remain consistent with handoff governance checks.

## Canonical references

- `docs/dod_manifest.json`
- `docs/system_contract_map.md`
- `docs/process/quality_stage_commands.json`
- `docs/sprint_handoffs/sprint-5-handoff.md`

## Evidence commands

- `pytest tests/test_validate_milestone_docs.py tests/test_governance_pr_evidence_validator.py`
- `pytest tests/test_sprint_handoff_validation.py`
- `python scripts/ci/validate_decision_records.py`
