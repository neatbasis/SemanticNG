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
| stability | `required-check-pass-rate` | `>= 98%` | Required-check pass rate on `Quality Guardrails` jobs and branch protection required-check history. |
| signal-health | `flaky-test-count` | `<= 2 count` | Flaky-test classification from CI rerun/failure artifacts. |
| staleness | `stale-doc-freshness-days` | `<= 30 days` | Process/governance doc freshness stamps and review checklist cadence. |
| supply-chain | `dependency-drift-count` | `<= 0 count` | `scripts/ci/check_toolchain_parity.py` results and dependency pin parity signals. |
| specification | `contract-maturity-movement` | `>= 0 net-level` | Contract maturity ledger movement across release readiness cycles. |

## Enforcement rollout

- Initial mode: all metrics run in `measure-only` to collect baselines during stabilization.
- Promotion window: non-blocking until `2026-04-15` (from JSON `stabilization_window.non_blocking_until`).
- Promotion action: CI validation step becomes blocking automatically after the stabilization window (or sooner by policy update).
