# Project Maturity Evaluation

_Last regenerated from manifest: 2026-02-28T15:48:35Z (UTC)._
_Regeneration command: `python .github/scripts/capability_parity_report.py` (then update this summary from `docs/dod_manifest.json` and `docs/system_contract_map.md`)._

## Executive assessment

SemanticNG is in an **authorization-first governance hardening** state.

All maturity claims in this document are derived from these canonical evidence sources only:

1. `docs/dod_manifest.json` (capability status, command packs, and CI evidence mappings).
2. `docs/system_contract_map.md` (contract maturity labels and promotion policy).

## Evidence snapshot (canonical-source derived)

### Capability delivery status (from `docs/dod_manifest.json`)

- **Done:** 7
- **In progress:** 0
- **Planned:** 2

Completion ratio (done / total): **77.8%** (`7/9`).

Current bottleneck capability (highest-priority non-`done`): **`capability_invocation_governance`**.

### Quality and validation signals (from `docs/dod_manifest.json`)

- Per-capability acceptance commands are canonical via `pytest_commands`.
- Validation command packs in this document are quoted directly from manifest `pytest_commands` entries.

### Contract maturity signal (from `docs/system_contract_map.md`)

- Contract maturity labels and promotion protocol are tracked in the contract map (`prototype`, `operational`, `proven`).

## Maturity conclusion

**Current stage: Post-replay governance maturation (authorization-first)**

Derived from canonical evidence:

- Governance and replay baseline capabilities are recorded as delivered in `docs/dod_manifest.json`.
- Remaining implementation work is concentrated in `capability_invocation_governance` and `repair_aware_projection_evolution` (`planned` in `docs/dod_manifest.json`).
- Contract maturity posture is governed by `docs/system_contract_map.md`.

## Most timely development (priority recommendation)

### #1 Immediate priority

**Prioritize `capability_invocation_governance` as the single current implementation target.**

### #2 Near-term execution sequence

1. **Start `capability_invocation_governance` (`Later`)**
   - `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py tests/test_predictions_contracts_and_gates.py`
2. **Then start `repair_aware_projection_evolution` (`Later`)**
   - `pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py`
   - `pytest tests/test_predictions_contracts_and_gates.py`

## Suggested maturity targets for next review window

- Keep done capabilities in non-regression coverage by validating manifest-defined command packs.
- Move `capability_invocation_governance` from `planned` toward executable baseline evidence.
- Recompute counts and bottleneck assignment from canonical sources only (`docs/dod_manifest.json` + `docs/system_contract_map.md`).

## Maturity changelog

- 2026-02-28T15:48:35Z: **Canonical manifest refresh** — deduplicated prior overlapping refresh notes into one event; recomputed totals (`7 done / 0 in_progress / 2 planned`), retained `capability_invocation_governance` as highest-priority non-done bottleneck, and aligned command packs to manifest `pytest_commands`.
- 2026-02-28T15:48:35Z: **Gate/halt evidence confirmation** — retained gate/halt baseline validation as canonical evidence under `docs/dod_manifest.json` command/evidence mappings and maturity interpretation in `docs/system_contract_map.md`.

## Maturity review protocol

Run a maturity review whenever one of these triggers occurs:

1. A capability status changes in `docs/dod_manifest.json` (especially `planned` → `in_progress` or `in_progress` → `done`).
2. A contract maturity level changes in `docs/system_contract_map.md` (`prototype`/`operational`/`proven`).
3. A milestone boundary changes (`Now`/`Next`/`Later`) in capability planning.
4. A manifest-listed validation command changes or fails.

For each review, execute this update sequence:

1. Recompute capability ratios directly from `docs/dod_manifest.json` and update `done`, `in_progress`, and `planned` totals.
2. Set the **current bottleneck capability** to the highest-priority non-`done` capability (prefer `in_progress`; otherwise blocking `planned`).
3. Verify contract maturity interpretation against `docs/system_contract_map.md` and update conclusions accordingly.
4. Pull validation command packs directly from `pytest_commands` arrays in `docs/dod_manifest.json` (no ad-hoc command variants).
5. Update the top metadata timestamp to the refresh-run generated UTC timestamp.

## Next milestone checkpoints

| Next milestone | Cadence target | Owner area | Pass criteria |
| --- | --- | --- | --- |
| Observer authorization contract activation | Next 2 sprint windows | Engine + Invariants | `pytest tests/test_observer_frame.py` and `pytest tests/test_predictions_contracts_and_gates.py tests/test_invariants.py` remain green with authorization-scope enforcement in default mission-loop paths. |
| Capability governance contract baseline | Next 2 sprint windows after observer checkpoint | Engine + Contracts | `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py tests/test_predictions_contracts_and_gates.py` passes with policy-aware capability invocation and no regression in prediction/halt/replay contracts. |
| Repair-aware projection evolution baseline | Following sprint window after governance baseline | Engine + Contracts + Invariants | `pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py` and `pytest tests/test_predictions_contracts_and_gates.py` establish auditable repair-event lineage without regressing append-only replay guarantees. |
