# 5S metrics specification

Machine-readable source: `docs/process/5s_metrics.json`.

This document defines the operational 5S metric model and maps each metric to existing quality signals already emitted by repository workflows and governance surfaces.

## Field contract (per metric)

Every metric entry in the JSON spec contains:

- `s`: 5S category.
- `metric_id`: stable machine-readable metric identifier.
- `definition`: concise natural-language definition.
- `source_of_truth`: canonical system or artifact used for measurement.
- `target_threshold`: threshold object (`operator`, `value`, `unit`).
- `breach_severity`: `low|medium|high|critical` impact class.
- `enforcement_mode`: `measure-only` or `blocking`.

## Metric catalog and signal mapping

| S | Metric ID | Target threshold | Existing signal mapping |
| --- | --- | --- | --- |
| stability | `required-check-pass-rate` | `>= 98%` | .github/workflows/quality-guardrails.yml job outcomes + branch protection required-check logs |
| signal-health | `flaky-test-count` | `<= 2 count` | CI rerun diagnostics and failure classification artifacts |
| staleness | `stale-doc-freshness-days` | `<= 30 days` | docs/process review timestamps and freshness checklist updates |
| supply-chain | `dependency-drift-count` | `<= 0 count` | scripts/ci/check_toolchain_parity.py output and lockfile drift reports |
| specification | `contract-maturity-movement` | `>= 0 net-level` | Contract maturity ledger and release readiness checklist deltas |
| sort | `unused_symbol_count_core` | `<= 0 new-count` | `python scripts/ci/scan_unused_code.py` writes deterministic machine-readable findings to `artifacts/unused_code/core_unused.json`; non-zero findings are blocking in CI |
| sort | `unused_symbol_count_state_renorm` | `<= 0 new-count` | `python scripts/ci/scan_unused_code.py` writes deterministic machine-readable findings to `artifacts/unused_code/state_renormalization_unused.json`; non-zero findings are blocking in CI |
| sort | `unused_symbol_count_features` | `<= 0 new-count` | `python scripts/ci/scan_unused_code.py` writes deterministic machine-readable findings to `artifacts/unused_code/features_unused.json`; findings are warning-level/non-blocking until promotion |
| sort | `orphan_module_count` | `<= 0 count` | Import-graph reachability report from canonical entrypoints and orphan-module detector artifact |
| sort | `duplicate_logic_cross_surface` | `<= 0 count` | Cross-surface duplication scan report and architectural review adjudication log |

## Enforcement rollout

- CI now runs `python scripts/ci/validate_5s_metrics.py`, emitting `artifacts/5s_metrics_validation.md` and `artifacts/5s_metrics_validation.json` before broader QA checks.
- CI now runs `python scripts/ci/scan_unused_code.py`, emitting per-surface artifacts under `artifacts/unused_code/` plus aggregate `artifacts/unused_code/summary.json`.
- Current mode: canonical Sort metrics for `core` and `state_renormalization` run in `blocking`; feature-surface Sort tracking remains `measure-only` (warning-level output) until promotion.
- Promotion window: non-blocking until `2026-04-15` (from JSON `stabilization_window.non_blocking_until`).
- Promotion action: CI validation step promotes remaining `measure-only` metrics to blocking after the stabilization window (or sooner by policy update).

## Unused-code analytics readiness (sort metrics)

Current maintainers' assessment: **partially ready** for strict governance use.

### Ready now

- The scanner is deterministic: `scripts/ci/scan_unused_code.py` defines explicit surfaces, sorts diagnostics for stable output, and emits per-surface plus summary JSON artifacts under `artifacts/unused_code/`.
- Governance wiring is in place: `qa-ci` includes `python scripts/ci/scan_unused_code.py` in `docs/process/quality_stage_commands.json`.
- Policy split is explicit by surface: `core` and `state_renormalization` are blocking; `features` remains warning/non-blocking until promotion.

### Gaps to close before treating this as fully mature

- Signal scope is currently narrow (`Ruff F401,F841`), which covers unused imports and locals but not broad dead-symbol classes (e.g., unused functions/classes/modules).
- Some policy text in governance docs references baseline/allowlist diffs; current scanner implementation enforces from direct current findings, so policy and implementation should be aligned.
- Add dedicated scanner contract tests (`tests/test_scan_unused_code.py`) for deterministic ordering, artifact schema, surface-level blocking behavior, and Ruff error-path handling.
