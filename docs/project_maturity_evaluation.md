# Project Maturity Evaluation (2026-02-28)

## Executive assessment

SemanticNG is in an **authorization-first governance hardening** state:

- Core baseline capabilities remain implemented and tested.
- Capability accounting from the manifest is `6/9` done.
- There are currently **no** `in_progress` capabilities in the manifest; the active delivery bottleneck is the highest-priority `planned` item: `observer_authorization_contract`.

## Evidence snapshot

### Capability delivery status (from DoD manifest)

- **Done:** 6
- **In progress:** 0
- **Planned:** 3

Completion ratio (done / total): **66.7%** (`6/9`).

Current bottleneck capability (highest-priority non-`done`): **`observer_authorization_contract`**.

Rationale:

1. It is the only capability in roadmap section `Next`.
2. `replay_projection_analytics` is already `done` (not an in-progress bottleneck).
3. Remaining non-done capabilities are both `Later` (`capability_invocation_governance`, `repair_aware_projection_evolution`).

### Quality and validation signals

- Manifest acceptance commands are defined per capability via `pytest_commands` in `docs/dod_manifest.json`.
- Immediate-priority validation commands for `observer_authorization_contract` are:
  - `pytest tests/test_observer_frame.py`
  - `pytest tests/test_predictions_contracts_and_gates.py tests/test_invariants.py`
- Contract map defines explicit maturity labels (`prototype`, `operational`, `proven`) and promotion protocol.
- Replay and halt capabilities remain in `done` and should continue running as non-regression evidence packs.

### Lifecycle/process signals

- Repository documents a clear document lifecycle and milestone structure.
- Current sequencing is authorization contract promotion first, then governance, then repair-aware evolution.

## Maturity conclusion

**Current stage: Post-replay governance maturation (authorization-first)**

The project has:

- Strong foundational contracts and deterministic behavior coverage.
- Replay-grade projection reconstruction and restart analytics delivered as `done` capabilities.
- Hardened halt behavior and invariant-matrix validation in the done baseline.

It does **not yet** have:

- Observer authorization promoted beyond `planned`/`prototype`.
- Capability-invocation governance and repair-aware projection capabilities implemented.

## Most timely development (priority recommendation)

### #1 Immediate priority

**Prioritize `observer_authorization_contract` as the single current implementation target.**

Why this is most timely:

1. It is the highest-priority non-done capability (`Next`).
2. No capabilities are currently marked `in_progress`, so this is the clear next execution slot.
3. It is a prerequisite sequencing gate before both `Later` governance and repair-aware scopes.

### #2 Concrete near-term execution sequence

1. **Land runtime observer authorization enforcement (`Next`)**
   - Execute and keep green the manifest commands:
     - `pytest tests/test_observer_frame.py`
     - `pytest tests/test_predictions_contracts_and_gates.py tests/test_invariants.py`
2. **Promote Observer authorization contract maturity**
   - Update contract-map maturity after stable default-path enforcement evidence.
3. **Start `capability_invocation_governance` (`Later`)**
   - Use manifest commands:
     - `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py`
     - `pytest tests/test_predictions_contracts_and_gates.py`
4. **Then start `repair_aware_projection_evolution` (`Later`)**
   - Use manifest commands:
     - `pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py`
     - `pytest tests/test_predictions_contracts_and_gates.py`

## Suggested maturity targets for next review

- Promote observer authorization from `prototype` toward `operational` with CI-backed default-path enforcement evidence.
- Establish capability-invocation governance baseline evidence after observer authorization promotion.
- Recompute capability completion and confirm all `pytest_commands` for non-done capabilities are represented in CI checks.

## Maturity changelog

- 2026-02-28: **Refresh update** — recomputed capability totals from `docs/dod_manifest.json` (`6 done / 0 in_progress / 3 planned`), replaced stale replay-bottleneck framing with observer-authorization bottleneck framing, updated priority recommendation to `observer_authorization_contract`, and aligned command references to manifest `pytest_commands`.
- 2026-02-28: Sync pass — updated this evaluation to match manifest totals (`6 done / 0 in_progress / 3 planned`), roadmap sequencing (`observer_authorization_contract` as the sole `Next` item), and contract-map maturity framing (observer authorization still `prototype`); replay is treated as a maintained baseline rather than a bottleneck.
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
4. Attach concrete next-step validation commands so planning remains execution-focused.

### Review command pack (next-step execution anchors)

Use generated command packs from `docs/dod_manifest.json` to avoid list drift:

- PR template-ready checklist block (all capabilities + evidence URL placeholders):
  - `python .github/scripts/render_transition_evidence.py --emit-pr-template-autogen`
- Transition-only PR evidence block for the current branch diff:
  - `python .github/scripts/render_transition_evidence.py --base <base_sha> --head <head_sha>`

Narrative planning in this document should reference those generated outputs rather than copying raw pytest command lists inline.

## Next milestone checkpoints

| Next milestone | Target date | Owner area | Pass criteria |
| --- | --- | --- | --- |
| Observer authorization contract activation | 2026-03-22 | Engine + Invariants | `pytest tests/test_observer_frame.py` and `pytest tests/test_predictions_contracts_and_gates.py tests/test_invariants.py` are green with authorization-scope enforcement in default mission-loop paths. |
| Capability governance contract baseline | 2026-03-29 | Engine + Contracts | `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py` and `pytest tests/test_predictions_contracts_and_gates.py` pass with policy-aware capability invocation and no regression in prediction/halt/replay contracts. |
| Repair-aware projection evolution baseline | 2026-04-05 | Engine + Contracts + Invariants | `pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py` and `pytest tests/test_predictions_contracts_and_gates.py` establish auditable repair-event lineage without regressing append-only replay guarantees. |
