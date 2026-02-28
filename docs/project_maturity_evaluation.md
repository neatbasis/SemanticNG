# Project Maturity Evaluation (2026-02-28)

## Executive assessment

SemanticNG is in an **operational hardening** state:

- Core baseline capabilities are implemented and tested (`5/9` manifest capabilities are `done`, including `gate_halt_unification`).
- The entire current pytest suite is passing locally.
- The architecture has clear milestone framing (`Now` / `Next` / `Later`) and contract-level maturity tracking.
- The most critical unfinished work is now concentrated in replay-grade projection analytics and downstream governance expansion.

## Evidence snapshot

### Capability delivery status (from DoD manifest)

- **Done:** 5
- **In progress:** 1
- **Planned:** 3

Completion ratio (done / total): **55.6%** (`5/9`).

Current bottleneck capability: **`replay_projection_analytics`** (`in_progress`). Halt/gate unification acceptance is verified by the merged regression command (`82 passed, 4 skipped`), so replay-grade audit/analytics remains the highest-priority unresolved dependency for Later milestone confidence.

This indicates the project is beyond baseline contract hardening and entering replay/analytics completion work.

### Quality and validation signals

- Test suite currently passes (`pytest -q`).
- Roadmap items are linked to concrete test commands.
- Contract map defines explicit maturity labels (`prototype`, `operational`, `proven`) and promotion protocol.
- Halt normalization behavior is enforced through gate, mission-loop, persistence, and halt contract tests.

### Lifecycle/process signals

- Repository documents a clear document lifecycle and milestone structure.
- Recent commit history shows active iteration on invariants, halts, observer authorization, schema selection, and contract mapping.

## Maturity conclusion

**Current stage: Operational foundation / hardening in progress**

The project has:

- Strong foundational contracts and deterministic behavior coverage.
- A disciplined test-driven roadmap.
- Hardened and explainable halt normalization behavior across unified gate paths.

It does **not yet** have:

- Replay-grade longitudinal analytics maturity.
- Observer authorization and capability-governance contracts promoted beyond planned/prototype stages.

## Most timely development (priority recommendation)

### #1 Immediate priority

**Finish `replay_projection_analytics` (Later milestone) before expanding additional Later capabilities.**

Why this is most timely:

1. It is the only capability currently marked `in_progress` in the DoD manifest.
2. Halt/gate contract hardening is already merged, so replay determinism is now the dominant risk reducer.
3. It is a prerequisite for credible correction metrics and auditability claims in governance-heavy future features.

### #2 Concrete near-term execution sequence

1. **Complete replay projection parity**
   - Ensure reconstructed projection state is deterministic across prediction, correction, and restart sequences.
2. **Lock restart contract invariants**
   - Verify restart projections preserve halt explainability and outcome linkage contracts.
3. **Harden replay analytics assertions**
   - Keep correction/cost attribution derivations deterministic and lineage-backed in tests.

### #3 Defer until #1 is green

- Observer authorization expansion (`observer_authorization_contract`).
- Capability invocation governance.

Current analytics phase scope (read-only):
- Define minimal analytics contracts for correction counts/cost attribution.
- Derive analytics deterministically from persisted prediction/halt/correction lineage logs only.

Non-goals in this phase:
- No external integrations for BI/telemetry export.
- No runtime side effects or changes to mission-loop control flow from analytics derivation.
- Larger external capability governance surface expansion.

## Suggested maturity targets for next review

- Promote replay projection analytics from `in_progress` capability to `done` once replay determinism tests are stable in CI.
- Keep a dated changelog note in maturity docs for capability or contract maturity transitions.
- Recompute capability completion and confirm replay + observer tests pass in CI before promoting additional Later features.

## Maturity changelog

- 2026-02-28: Revalidated `gate_halt_unification` as `done` against its acceptance command (`pytest tests/test_predictions_contracts_and_gates.py tests/test_engine_projection_mission_loop.py tests/test_persistence_jsonl.py tests/test_contracts_halt_record.py` => `82 passed, 4 skipped`), and confirmed `replay_projection_analytics` remains the primary bottleneck.
- 2026-02-28: Updated maturity narrative from pre-hardening bottleneck to replay/analytics bottleneck after merged milestone-gate and halt/gate hardening outcomes; halt normalization is now treated as hardened/proven and no longer the principal blocker.

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

- `pytest tests/test_predictions_contracts_and_gates.py tests/test_engine_projection_mission_loop.py tests/test_persistence_jsonl.py tests/test_contracts_halt_record.py`
- `pytest tests/test_replay_projection_analytics.py tests/test_replay_projection_determinism.py tests/test_replay_projection_restart_contracts.py tests/test_prediction_outcome_binding.py`
- `pytest tests/test_observer_frame.py`

## Next milestone checkpoints

| Next milestone | Target date | Owner area | Pass criteria |
| --- | --- | --- | --- |
| Replay projection analytics completion | 2026-03-15 | Engine + Persistence + Contracts | `tests/test_replay_projection_analytics.py`, `tests/test_replay_projection_determinism.py`, and `tests/test_replay_projection_restart_contracts.py` are green with deterministic replay/restart parity. |
| Observer authorization contract activation | 2026-03-22 | Engine + Invariants | `tests/test_observer_frame.py` is green with authorization-scope enforcement in default mission-loop paths. |
| Capability governance contract baseline | 2026-03-29 | Engine + Contracts | Governance tests pass with policy-aware capability invocation and no regression in prediction/halt contracts. |
