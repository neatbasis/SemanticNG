# Project Maturity Evaluation

_Last regenerated from manifest: 2026-03-02T01:22:00Z (UTC)._
_Regeneration command: `python .github/scripts/capability_parity_report.py` (then update this summary from `docs/dod_manifest.json` and `docs/system_contract_map.md`)._

## Executive assessment

SemanticNG is in an **authorization-first governance hardening** state.

This **Executive assessment** section is the authoritative statement of the **current** project maturity state for this document revision.

All maturity claims in this document are derived from these canonical evidence sources only:

1. `docs/dod_manifest.json` (capability status, command packs, and CI evidence mappings).
2. `docs/system_contract_map.md` (contract maturity labels and promotion policy).

## Evidence snapshot (canonical-source derived)

This **Evidence snapshot** section is the authoritative **current-state** count and signal baseline, derived from canonical sources at the regeneration timestamp above.

### Capability delivery status (from `docs/dod_manifest.json`)

- **Done:** 9
- **In progress:** 0
- **Planned:** 0

Completion ratio (done / total): **100.0%** (`9/9`).

Current bottleneck set (remaining non-`done` implementation queue): _none (all manifest capabilities are `done`)_.

Current bottleneck capability: **`none`** (all manifest capabilities are `done`).

### Quality and validation signals (from `docs/dod_manifest.json`)

- Per-capability acceptance commands are canonical via `pytest_commands`.
- Validation command packs in this document are quoted directly from manifest `pytest_commands` entries.

### Contract maturity signal (from `docs/system_contract_map.md`)

- Contract maturity labels and promotion protocol are tracked in the contract map (`prototype`, `operational`, `proven`).

## 5S maturity posture

Concise posture sourced from `docs/5s_mission_traceability.md` (principle-to-governance mapping) and the current metric snapshot in `docs/process/5s_metrics.json`.

| 5S principle | Traceability posture (matrix-derived) | Current metric snapshot |
| --- | --- | --- |
| stability | Linked to predict-first and explainable-halt governance (`A2`, `A3`, `A8`) with CI/runtime gate enforcement. | `required-check-pass-rate`: `>= 98%`, mode `measure-only`. |
| signal-health | Linked to executable-spec + evidence governance (`A9`, `A10`) with flaky-signal workflow classification and test anchors. | `flaky-test-count`: `<= 2 count`, mode `measure-only`. |
| staleness | Linked to contract-boundary and governance freshness controls (`A5`, `A10`) with freshness/schema checks. | `stale-doc-freshness-days`: `<= 30 days`, mode `measure-only`. |
| supply-chain | Linked to contract/evidence policy controls (`A5`, `A9`) with parity drift checks. | `dependency-drift-count`: `<= 0 count`, mode `measure-only`. |
| specification | Linked to replay/audit and executable-governance controls (`A1`, `A7`, `A10`) with governance parity checks. | `contract-maturity-movement`: `>= 0 net-level`, mode `measure-only`. |

## Maturity conclusion

**Current stage: Next-entry governance execution with one active promotion and one queued dependency**

Derived from canonical evidence:

- Governance and replay baseline capabilities are recorded as delivered in `docs/dod_manifest.json`.
- All listed capabilities are currently `done` in `docs/dod_manifest.json`; focus remains on non-regression validation and evidence freshness.
- Contract maturity posture is governed by `docs/system_contract_map.md`.

## Most timely development (priority recommendation)

### #1 Immediate priority

**Maintain non-regression evidence quality across all `done` capabilities and keep governance artifacts synchronized.**

### #2 Near-term execution sequence

1. **Sustain `capability_invocation_governance` (`done`) non-regression evidence**
   - `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py tests/test_predictions_contracts_and_gates.py`
2. **Sustain `repair_aware_projection_evolution` (`done`) non-regression evidence**
   - `pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py`
   - `pytest tests/test_predictions_contracts_and_gates.py`

## Suggested maturity targets for next review window

- Keep done capabilities in non-regression coverage by validating manifest-defined command packs.
- Keep completed capabilities in regression coverage and refresh CI evidence links on cadence.
- Recompute counts and bottleneck-set assignment from canonical sources only (`docs/dod_manifest.json` + `docs/system_contract_map.md`).

## Maturity changelog

- 2026-03-02T01:22:00Z: **Historical snapshot — canonical maturity refresh (prior state, not current)** — at that time, capability totals were `7 done / 1 in_progress / 1 planned`; stage language reflected active Next-entry governance execution, and the bottleneck was completing `capability_invocation_governance` before promoting `repair_aware_projection_evolution`.
- 2026-03-02T00:53:00Z: **Historical snapshot — canonical maturity refresh (prior state, not current)** — at that time, capability totals were `7 done / 0 in_progress / 2 planned`; stage language reflected a late-Now completion posture, and the bottleneck was the two-capability planned queue (`capability_invocation_governance`, `repair_aware_projection_evolution`).
- 2026-02-28T15:48:35Z: **Historical snapshot — canonical manifest refresh (prior state, not current)** — at that time, totals were `7 done / 0 in_progress / 2 planned`; `capability_invocation_governance` remained the highest-priority non-done bottleneck, and command packs were aligned to manifest `pytest_commands`.
- 2026-02-28T15:48:35Z: **Historical snapshot — gate/halt evidence confirmation (prior state, not current)** — retained gate/halt baseline validation as then-current canonical evidence under `docs/dod_manifest.json` command/evidence mappings and maturity interpretation in `docs/system_contract_map.md`.

## Maturity review protocol

Run a maturity review whenever one of these triggers occurs:

1. A capability status changes in `docs/dod_manifest.json` (especially `planned` → `in_progress` or `in_progress` → `done`).
2. A contract maturity level changes in `docs/system_contract_map.md` (`prototype`/`operational`/`proven`).
3. A milestone boundary changes (`Now`/`Next`/`Later`) in capability planning.
4. A manifest-listed validation command changes or fails.

For each review, execute this update sequence:

1. Recompute capability ratios directly from `docs/dod_manifest.json` and update `done`, `in_progress`, and `planned` totals.
2. Set the **current bottleneck capability/set** to the highest-priority non-`done` work queue (prefer `in_progress`; otherwise the remaining blocking `planned` capabilities).
3. Verify contract maturity interpretation against `docs/system_contract_map.md` and update conclusions accordingly.
4. Pull validation command packs directly from `pytest_commands` arrays in `docs/dod_manifest.json` (no ad-hoc command variants).
5. Update the top metadata timestamp to the refresh-run generated UTC timestamp.

## Next milestone checkpoints

| Next milestone | Cadence target | Owner area | Pass criteria |
| --- | --- | --- | --- |
| Observer authorization contract activation | Next 2 sprint windows | Engine + Invariants | `pytest tests/test_observer_frame.py` and `pytest tests/test_predictions_contracts_and_gates.py tests/test_invariants.py` remain green with authorization-scope enforcement in default mission-loop paths. |
| Capability governance contract baseline | Next 2 sprint windows after observer checkpoint | Engine + Contracts | `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py tests/test_predictions_contracts_and_gates.py` passes with policy-aware capability invocation and no regression in prediction/halt/replay contracts. |
| Repair-aware projection evolution baseline | Following sprint window after governance baseline | Engine + Contracts + Invariants | `pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py` and `pytest tests/test_predictions_contracts_and_gates.py` establish auditable repair-event lineage without regressing append-only replay guarantees. |
