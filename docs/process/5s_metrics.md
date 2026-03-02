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
| sort | `unused_symbol_count_core` | `<= 0 new-count` | Per-surface unused-symbol scan output (Vulture default) for src/core plus baseline allowlist diff artifact |
| sort | `unused_symbol_count_state_renorm` | `<= 0 new-count` | Per-surface unused-symbol scan output (Vulture default) for src/state_renormalization plus baseline allowlist diff artifact |
| sort | `unused_symbol_count_features` | `<= 0 new-count` | Per-surface unused-symbol scan output (Vulture default) for src/features with capability-mapping review notes |
| sort | `orphan_module_count` | `<= 0 count` | Import-graph reachability report from canonical entrypoints and orphan-module detector artifact |
| sort | `duplicate_logic_cross_surface` | `<= 0 count` | Cross-surface duplication scan report and architectural review adjudication log |

## Enforcement rollout

- Current mode: canonical Sort metrics for `core` and `state_renormalization` run in `blocking`; feature-surface Sort tracking remains `measure-only` until promotion.
- Promotion window: non-blocking until `2026-04-15` (from JSON `stabilization_window.non_blocking_until`).
- Promotion action: CI validation step promotes remaining `measure-only` metrics to blocking after the stabilization window (or sooner by policy update).
