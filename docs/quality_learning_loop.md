# Quality Learning Loop

This document defines the required response SLA for failures surfaced by pre-commit governance telemetry.

## Classification taxonomy

Each pre-commit run is classified into one or more stable keys:

- `ruff`
- `mypy`
- `pytest`
- `infra_setup`

## Required response SLA

For every classified failure cluster, triage must produce all of the following fields in the tracking issue or incident comment:

1. **Owner**: directly responsible engineer (single DRI).
2. **Decision**: either `fix` or `waiver`.
3. **Due date**: target completion date in `YYYY-MM-DD`.

### Time bounds

- Initial triage (owner + decision + due date): within **1 business day** of detection.
- `fix` decisions: remediation merged within **5 business days**.
- `waiver` decisions: waiver rationale + expiry date captured within **2 business days**.

## Weekly governance cadence

A weekly workflow aggregates the previous 7 days of classification artifacts and summarizes:

- failure counts by taxonomy class,
- touched paths observed in logs.

The summary is published as machine-readable JSON and Markdown for quality trend analysis.
