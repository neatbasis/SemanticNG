# Project Maturity Evaluation (2026-02-28)

## Executive assessment

SemanticNG is in an **authorization-first governance hardening** state:

- Core baseline capabilities remain implemented and tested.
- Capability accounting recomputed from `docs/dod_manifest.json` is `7/9` done.
- There are currently **no** `in_progress` capabilities in the manifest; the active delivery bottleneck is the highest-priority `planned` item: `capability_invocation_governance`.

## Evidence snapshot

### Capability delivery status (from DoD manifest)

- **Done:** 7
- **In progress:** 0
- **Planned:** 2

Completion ratio (done / total): **77.8%** (`7/9`).

Current bottleneck capability (highest-priority non-`done`): **`capability_invocation_governance`**.

Rationale:

1. `observer_authorization_contract` is now `done`; the next non-done dependency-unblocked capability is `capability_invocation_governance`.
2. `replay_projection_analytics` is `done` in the manifest and treated as maintained baseline coverage, not an in-progress bottleneck.
3. The other non-done capabilities are `Later` (`capability_invocation_governance`, `repair_aware_projection_evolution`).

### Quality and validation signals

- Manifest acceptance commands are canonical per capability via `pytest_commands` in `docs/dod_manifest.json`.
- Immediate-priority validation command pack for `capability_invocation_governance` (exact manifest set):
  - `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py`
  - `pytest tests/test_predictions_contracts_and_gates.py`
- Replay non-regression command pack for `replay_projection_analytics` (exact manifest set):
  - `pytest tests/test_predictions_contracts_and_gates.py tests/test_persistence_jsonl.py`
  - `pytest tests/test_replay_projection_analytics.py tests/test_replay_projection_determinism.py tests/test_replay_projection_restart_contracts.py tests/test_prediction_outcome_binding.py`
  - `pytest tests/replay_projection_analytics/test_append_only_replay.py`
- Contract map defines explicit maturity labels (`prototype`, `operational`, `proven`) and promotion protocol.

### Lifecycle/process signals

- Repository documents a clear document lifecycle and milestone structure.
- Current sequencing is governance hardening next, then repair-aware evolution.

## Maturity conclusion

**Current stage: Post-replay governance maturation (authorization-first)**

The project has:

- Strong foundational contracts and deterministic behavior coverage.
- Replay-grade projection reconstruction and restart analytics delivered as `done` capabilities.
- Hardened halt behavior and invariant-matrix validation in the done baseline.

It does **not yet** have:

- Capability-invocation governance implemented.
- Repair-aware projection evolution implemented.

## Most timely development (priority recommendation)

### #1 Immediate priority

**Prioritize `capability_invocation_governance` as the single current implementation target.**

Why this is most timely:

1. It is the highest-priority non-done capability after observer authorization completion.
2. No capabilities are currently marked `in_progress`, so this is the clear next execution slot.
3. It is a prerequisite sequencing gate before both `Later` governance and repair-aware scopes.

### #2 Concrete near-term execution sequence

1. **Start `capability_invocation_governance` (`Later`)**
   - Execute the exact manifest `pytest_commands`:
     - `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py`
     - `pytest tests/test_predictions_contracts_and_gates.py`
2. **Then start `repair_aware_projection_evolution` (`Later`)**
   - Execute the exact manifest `pytest_commands`:
     - `pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py`
     - `pytest tests/test_predictions_contracts_and_gates.py`

## Suggested maturity targets for next review

- Maintain observer authorization as `operational` with CI-backed non-regression evidence.
- Establish capability-invocation governance baseline evidence as the next dependency-unblocked implementation scope.
- Recompute capability completion and confirm all `pytest_commands` for non-done capabilities are represented in CI checks.

## Maturity changelog

- 2026-02-28: **Maturity refresh (manifest-derived)** — recomputed status totals directly from `docs/dod_manifest.json` (`7 done / 0 in_progress / 2 planned`), confirmed `capability_invocation_governance` as the highest-priority non-done bottleneck, and synchronized all listed command packs to their exact manifest `pytest_commands` definitions (including replay analytics non-regression packs).
- 2026-02-28: **Manifest synchronization pass** — recomputed capability totals directly from `docs/dod_manifest.json` (`7 done / 0 in_progress / 2 planned`), reaffirmed `capability_invocation_governance` as the highest-priority non-done bottleneck, replaced stale replay-bottleneck framing with replay-as-done-baseline wording, and normalized listed validation command packs to exact manifest `pytest_commands`.
- 2026-02-28: Revalidated `gate_halt_unification` as `done` against its acceptance command (`pytest tests/test_predictions_contracts_and_gates.py tests/test_engine_projection_mission_loop.py tests/test_persistence_jsonl.py tests/test_contracts_halt_record.py` => `92 passed, 4 skipped`).
- 2026-02-28: Confirmed `tests/test_predictions_contracts_and_gates.py` enforces deterministic `Flow.CONTINUE`/`Flow.STOP` parity assertions and `tests/test_persistence_jsonl.py` verifies halt payload durability for canonical `details`, `evidence`, and invariant identity (`invariant_id`) round-trips.

## Maturity review protocol

Run a maturity review whenever one of these triggers occurs:

1. A capability status changes in `docs/dod_manifest.json` (especially `planned` → `in_progress` or `in_progress` → `done`).
2. A contract maturity level changes in `docs/system_contract_map.md` (`prototype`/`operational`/`proven`).
3. A milestone boundary is crossed (`Now`/`Next`/`Later`) or a milestone target date is reached.
4. A critical gate/halt or replay regression test command changes or starts failing.

For each review, execute this update sequence:

1. Recompute capability ratios directly from `docs/dod_manifest.json` and update this document with current `done`, `in_progress`, and `planned` totals.
2. Set the **current bottleneck capability** to the highest-priority non-`done` capability (prefer `in_progress`; otherwise the blocking `planned` item with the most dependency surface).
3. Add or update dated maturity promotion entries in `docs/system_contract_map.md` changelog, including rationale and milestone context.
4. Pull validation command packs directly from the target capability `pytest_commands` arrays in `docs/dod_manifest.json` (avoid ad-hoc command edits in this document).

## Next milestone checkpoints

| Next milestone | Target date | Owner area | Pass criteria |
| --- | --- | --- | --- |
| Observer authorization contract activation | 2026-03-22 | Engine + Invariants | `pytest tests/test_observer_frame.py` and `pytest tests/test_predictions_contracts_and_gates.py tests/test_invariants.py` are green with authorization-scope enforcement in default mission-loop paths. |
| Capability governance contract baseline | 2026-03-29 | Engine + Contracts | `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py` and `pytest tests/test_predictions_contracts_and_gates.py` pass with policy-aware capability invocation and no regression in prediction/halt/replay contracts. |
| Repair-aware projection evolution baseline | 2026-04-05 | Engine + Contracts + Invariants | `pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py` and `pytest tests/test_predictions_contracts_and_gates.py` establish auditable repair-event lineage without regressing append-only replay guarantees. |
