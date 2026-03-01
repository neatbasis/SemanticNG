# Definition of Complete

This document is the canonical definition of completion for `state_renormalization` capabilities tracked in `docs/dod_manifest.json`.

## Completion layers

### 1) Capability-complete

A capability is **capability-complete** when:

- Module-level contracts are implemented and validated in the capability's `pytest_commands` listed in `docs/dod_manifest.json`.
- Contract shapes and invariant gate behavior are covered by tests for the capability-owned modules.
- Required artifacts produced by the capability are deterministic and persistable for the scope it claims.

Typical evidence:

- Capability-specific command(s) in `pytest_commands`.
- Matching contract references in `contract_map_refs` that align with `docs/system_contract_map.md`.

### 2) Integration-complete

A capability is **integration-complete** when:

- Cross-capability flows that consume its artifacts pass end-to-end test paths.
- Upstream/downstream dependency behavior remains stable under shared mission-loop execution.
- Fail-closed behavior is preserved when dependencies are absent, invalid, or unauthorized.

Typical evidence:

- Cross-suite runs touching multiple capability commands.
- Replay/projection and gate-path regressions that prove interoperability.

### 3) System-complete

A capability (or coherent group of capabilities) is **system-complete** when:

- Operability is established (CI-ready checks, deterministic startup/shutdown behavior, and clear ownership).
- Replay and restart behavior is deterministic from append-only artifacts.
- Governance controls are enforceable (authorization scope, policy-aware gating, explicit stop conditions).
- Auditability is retained (explainable halt payloads, lineage-preserving artifacts, reproducible evidence links).

Typical evidence:

- CI evidence links attached in `docs/dod_manifest.json`.
- Contract maturity progression in `docs/system_contract_map.md` from `operational` to `proven` where applicable.

## Enablement matrix (from `docs/dod_manifest.json`)

| Capability (`id`) | Prerequisites consumed | Downstream capabilities unlocked | Shared support provided when mature |
|---|---|---|---|
| `prediction_persistence_baseline` | None (foundation capability). | `gate_halt_unification`, `replay_projection_analytics`, `repair_aware_projection_evolution`. | Stable IDs + append-only prediction persistence baseline for all projection/gate flows. |
| `channel_agnostic_pending_obligation` | `prediction_persistence_baseline`. | `schema_selection_ambiguity_baseline`, `capability_invocation_governance`. | Canonical decision/effect and pending-obligation shapes reusable across channels and adapters. |
| `schema_selection_ambiguity_baseline` | `channel_agnostic_pending_obligation`. | `repair_aware_projection_evolution`. | Consistent schema-selection ambiguity contracts and pending-question carry-forward semantics. |
| `gate_halt_unification` | `prediction_persistence_baseline`, `channel_agnostic_pending_obligation`. | `invariant_matrix_coverage`, `replay_projection_analytics`, `capability_invocation_governance`. | Unified explainable-stop path and durable halt persistence shared by all guarded flows. |
| `observer_authorization_contract` | `gate_halt_unification`. | `capability_invocation_governance`. | Reusable observer scope envelope and authorization gate hooks for policy checks. |
| `replay_projection_analytics` | `prediction_persistence_baseline`, `gate_halt_unification`, `invariant_matrix_coverage`. | `repair_aware_projection_evolution`. | Deterministic replay/restart reconstruction and correction analytics for audit and debugging. |
| `invariant_matrix_coverage` | `gate_halt_unification`. | `replay_projection_analytics`, `capability_invocation_governance`, `repair_aware_projection_evolution`. | Exhaustive invariant branch assertions and non-applicable markers as shared regression safety net. |
| `capability_invocation_governance` | `observer_authorization_contract`, `invariant_matrix_coverage`, `channel_agnostic_pending_obligation`. | `repair_aware_projection_evolution` (policy-safe repair invocation paths). | Policy-aware side-effect gating contract usable by future external capability adapters. |
| `repair_aware_projection_evolution` | `replay_projection_analytics`, `schema_selection_ambiguity_baseline`, `capability_invocation_governance`. | N/A (current frontier capability). | Auditable repair-event evolution model without silent state mutation. |

## `state_renormalization` explicit completion gates

A change is not complete for this module until all gates below pass.

### Gate A: invariant safety

- Every changed invariant path has deterministic `Flow.CONTINUE`/`Flow.STOP` coverage.
- Non-applicable branches are explicitly asserted where defined.
- Halt events produced by invariant failures include required explainability fields.

Minimum evidence baseline:

- `tests/test_predictions_contracts_and_gates.py`
- `tests/test_invariants.py`

### Gate B: policy governance

- Observer authorization scope is enforced before capability-side effects.
- Unauthorized operations fail closed with explainable halts.
- Policy contract behavior is stable for both default and provided observers.

Minimum evidence baseline:

- `tests/test_observer_frame.py`
- Relevant governance-oriented gate suites as they are added (for example, capability invocation governance tests).

### Gate C: replay/restart determinism

- Replaying append-only artifacts reconstructs equivalent projection state across reruns.
- Restart scenarios produce deterministic analytics outcomes independent of process lifetime.
- No hidden side channels are required to rebuild correction lineage.

Minimum evidence baseline:

- `tests/test_replay_projection_determinism.py`
- `tests/test_replay_projection_restart_contracts.py`
- `tests/replay_projection_analytics/test_append_only_replay.py`

### Gate D: explainability of halts/repairs

- Every halt includes invariant identifier, human-readable details, and evidence payload.
- Repair-path changes (when enabled) emit explicit, auditable repair artifacts; no silent mutation.
- Halt/repair rationale must be recoverable from persisted artifacts alone.

Minimum evidence baseline:

- `tests/test_contracts_halt_record.py`
- `tests/test_engine_projection_mission_loop.py`
- Replay analytics suites that verify lineage recovery.

## Usage notes

- `docs/dod_manifest.json` remains the machine-readable source of capability status and test commands.
- This document defines when those capabilities are considered complete at capability, integration, and system layers.
- `docs/system_contract_map.md` remains the source of truth for contract maturity and changelog evidence.

_Last regenerated from manifest: 2026-03-01T00:00:00Z (UTC)._
