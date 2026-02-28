# Project Maturity Evaluation (2026-02-28)

## Executive assessment

SemanticNG is in an **operational hardening** state with replay completion now effectively achieved and remaining work concentrated in policy/governance expansion:

- Core baseline capabilities remain implemented and tested.
- Capability accounting from the manifest is still `5/9` done, with one entry pending status-sync housekeeping.
- Roadmap and contract-map narratives now treat replay projection analytics as completed implementation work, shifting the practical bottleneck to authorization/governance rollout.

## Evidence snapshot

### Capability delivery status (from DoD manifest)

- **Done:** 5
- **In progress:** 1
- **Planned:** 3

Completion ratio (done / total): **55.6%** (`5/9`).

Status-sync note: `replay_projection_analytics` is still marked `in_progress` in `docs/dod_manifest.json`, but roadmap and contract-map framing now treat replay work as functionally complete/done and no longer the principal execution blocker. The current bottleneck is therefore **authorization/governance activation** (`observer_authorization_contract` followed by `capability_invocation_governance`).

This indicates the project is beyond replay completion and entering governance hardening + expansion sequencing.

### Quality and validation signals

- Test suite currently passes (`pytest -q`).
- Roadmap items are linked to concrete test commands.
- Contract map defines explicit maturity labels (`prototype`, `operational`, `proven`) and promotion protocol.
- Halt normalization and replay analytics validation packs are now part of regular milestone evidence.

### Lifecycle/process signals

- Repository documents a clear document lifecycle and milestone structure.
- Recent updates are concentrated on deterministic replay/restart behavior and governance sequencing.

## Maturity conclusion

**Current stage: Post-replay operational hardening / governance maturation**

The project has:

- Strong foundational contracts and deterministic behavior coverage.
- Replay-grade projection reconstruction and analytics validation coverage in active command packs.
- Hardened and explainable halt normalization behavior across unified gate paths.

It does **not yet** have:

- Observer authorization and capability-governance contracts promoted beyond planned/prototype stages.
- Full governance-path maturity across external capability invocation surfaces.

## Most timely development (priority recommendation)

### #1 Immediate priority

**Prioritize `observer_authorization_contract` and then `capability_invocation_governance` (do not treat replay completion as the next blocker).**

Why this is most timely:

1. Replay completion is no longer the practical bottleneck in roadmap/contract-map execution framing.
2. Authorization semantics are the gating dependency for safe policy-aware capability invocation.
3. Governance expansion now provides the largest incremental risk reduction for Later milestone confidence.

### #2 Concrete near-term execution sequence

1. **Land runtime observer authorization enforcement**
   - Promote authorization checks from prototype-only contract framing to default-path runtime behavior.
2. **Stabilize governance policy guardrails**
   - Add deterministic tests for allowed/denied capability invocation outcomes.
3. **Preserve replay/halt regressions as non-regression gates**
   - Keep replay/restart + halt explainability packs green while governance work lands.

### #3 Defer until #1 is green

- Repair-aware projection evolution.
- Any broad external integration surface expansion.

## Suggested maturity targets for next review

- Sync `docs/dod_manifest.json` capability status for `replay_projection_analytics` to `done` once governance docs complete the same review cycle.
- Promote observer authorization from `prototype` toward `operational` with CI-backed default-path enforcement evidence.
- Recompute capability completion and confirm observer + governance tests pass in CI before expanding repair-aware scope.

## Maturity changelog

- 2026-02-28: Synced this maturity evaluation with current roadmap/contract-map direction and manifest command groupings; replay completion is no longer treated as the next priority, with focus shifted to authorization/governance sequencing.
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

- **Done capability command groups**
  - `pytest tests/test_stable_ids.py tests/test_persistence_jsonl.py tests/test_predictions_contracts_and_gates.py`
  - `pytest tests/test_contracts_belief_state.py tests/test_contracts_decision_effect_shape.py tests/test_engine_pending_obligation.py tests/test_engine_pending_obligation_minimal.py`
  - `pytest tests/test_schema_selector.py tests/test_schema_bubbling_option_a.py tests/test_capture_outcome_states.py tests/test_engine_calls_selector_with_generic_error.py`
  - `pytest tests/test_predictions_contracts_and_gates.py tests/test_engine_projection_mission_loop.py tests/test_persistence_jsonl.py tests/test_contracts_halt_record.py`
  - `pytest tests/test_predictions_contracts_and_gates.py`

- **Replay/analytics command groups (status-sync candidate)**
  - `pytest tests/test_predictions_contracts_and_gates.py tests/test_persistence_jsonl.py`
  - `pytest tests/test_replay_projection_analytics.py tests/test_replay_projection_determinism.py tests/test_replay_projection_restart_contracts.py tests/test_prediction_outcome_binding.py`
  - `pytest tests/replay_projection_analytics/test_append_only_replay.py`

- **Planned capability command groups**
  - `pytest tests/test_observer_frame.py`
  - `pytest tests/test_predictions_contracts_and_gates.py tests/test_invariants.py`
  - `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py`
  - `pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py`

## Next milestone checkpoints

| Next milestone | Target date | Owner area | Pass criteria |
| --- | --- | --- | --- |
| Observer authorization contract activation | 2026-03-22 | Engine + Invariants | `tests/test_observer_frame.py` is green with authorization-scope enforcement in default mission-loop paths. |
| Capability governance contract baseline | 2026-03-29 | Engine + Contracts | Governance tests pass with policy-aware capability invocation and no regression in prediction/halt/replay contracts. |
| Repair-aware projection evolution baseline | 2026-04-05 | Engine + Contracts + Invariants | Repair-mode tests establish auditable repair-event lineage without regressing append-only replay guarantees. |
