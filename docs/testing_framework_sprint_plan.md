# Testing Framework Assessment and Sprint Fix Plan

## Scope and baseline

This assessment validates the repository test harness via the primary runner (`pytest`) and promotion governance checks (`make promotion-checks`) and then proposes a phased remediation plan for observed failures.

## Validation results

- `pytest` fails early in `tests/test_capability_parity_report.py::test_deterministic_parity_mismatches_is_empty_for_repo_state`.
- Failure mode: the parity script treats changelog entries in `docs/system_contract_map.md` as unknown contracts when lines include the required `capability_id=<id>;` prefix.
- `make promotion-checks` passes, indicating that milestone-governance scripts and PR template autogen checks are currently healthy.

## Root-cause hypothesis

The changelog parser in `.github/scripts/capability_parity_report.py` uses a transition regex that expects the contract name to begin immediately after `:`, but actual changelog lines use the form:

`- YYYY-MM-DD (Milestone): capability_id=<id>; <contract> <from> -> <to>; ...`

This causes parsing to capture `capability_id=...; <contract>` as the contract identifier and miss table row matches.

## Remediation plan (separate sprints)

### Sprint 1 — Restore deterministic parity signal (hotfix)

**Goal:** make the parity check reliable again and unblock full-suite `pytest`.

**Planned work**
- Update transition parsing in `.github/scripts/capability_parity_report.py` to explicitly support the documented changelog format that includes `capability_id=<id>;`.
- Add/adjust unit tests in `tests/test_capability_parity_report.py` for both accepted formats (with and without capability prefix if backward compatibility is desired).
- Ensure parsing logic validates and extracts:
  - capability ID (optional for backward compatibility),
  - canonical contract name,
  - maturity transition (`from -> to`),
  - required evidence URL.

**Exit criteria**
- `pytest tests/test_capability_parity_report.py` passes.
- `pytest` full suite proceeds past the parity gate.

### Sprint 2 — Harden parser-contract governance

**Goal:** prevent future drift between docs and parser expectations.

**Planned work**
- Centralize changelog-line regex/pattern constants in one helper and document exact accepted grammar inline.
- Add negative tests for malformed lines (missing semicolon, malformed capability ID, unknown maturity token, absent evidence URL).
- Add a targeted script mode (or test helper) to emit actionable diagnostics (`line number`, `expected token`, `actual token`) for faster triage.

**Exit criteria**
- Expanded parity-report tests cover format success/failure matrix.
- Failure messages identify offending changelog line and exact parse reason.

### Sprint 3 — Improve testing-framework observability and CI ergonomics

**Goal:** reduce MTTR when governance tests fail and improve contributor confidence.

**Planned work**
- Add a dedicated Make target for parity diagnostics (e.g., `make parity-check`) that runs only parity-related checks.
- Document triage workflow in `tests/README.md` and/or `docs/release_checklist.md` (how to reproduce, interpret, and fix parity failures).
- Optionally add a CI job annotation step to surface parity mismatches as structured summaries in job output.

**Exit criteria**
- Contributors can reproduce parity failures with one command.
- Documentation includes a short “if parity fails, do X” path.
- CI output clearly separates formatting errors, unknown-contract errors, and maturity-transition errors.

## Suggested sequencing

1. Sprint 1 first (production unblocker).
2. Sprint 2 second (quality + regression prevention).
3. Sprint 3 third (developer-experience and operational excellence).
