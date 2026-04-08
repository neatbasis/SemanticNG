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


### Gate E: sprint substrate value increment

- Each sprint must include **at least one** delivered increment that is user-visible or provides clear external value, and that increment must be explicitly tied to substrate capabilities/governance in this repository.
- Sprint-close evidence must link the increment to the enabling substrate contract(s), gate(s), or replay/governance artifact(s) it depends on.
- If no qualifying increment is shipped, sprint close is incomplete and requires an explicit governance waiver with owner, rationale, and recovery sprint.

Accepted evidence examples (at least one per sprint):

1. A new end-to-end scenario demonstrating real decision value.
2. An external adapter integration with policy gating.
3. A deterministic replay artifact that answers a concrete product question.


## Promotion synchronization + handoff protocol

Capability status/maturity promotions are only complete when the governance triplet and progress artifact are updated together in one PR:

- `docs/dod_manifest.json`
- `docs/system_contract_map.md`
- `ROADMAP.md` and at least one active progress document (`docs/sprint_plan_5x.md` or sprint handoff)

Required command:

```bash
make promotion-check
```

Explicit handoff ownership:

1. **Capability owner** proposes status transition + command/evidence updates in `docs/dod_manifest.json`.
2. **Contract owner** applies matching maturity/changelog updates in `docs/system_contract_map.md`.
3. **Program/roadmap owner** mirrors transition status in roadmap/progress docs.
4. **Release/governance owner** executes `make promotion-check` and records a pass before merge.

### Explicit promotion criteria by sprint (required before promotion synchronization)

| Sprint | Promotion criterion (must be shipped) | Rollback trigger | Owner role |
| --- | --- | --- | --- |
| Sprint 1 | Schema + validator + deterministic naming are shipped and evidenced in sprint-close artifacts before promotion docs are advanced. | Any schema/validator parity drift or deterministic naming mismatch is detected by parity validators, freshness checks, or command-pack evidence review. | **Capability owner** initiates rollback to pre-promotion status and updates manifest evidence links. |
| Sprint 2 | Single orchestrator + fail-fast enforcement are shipped and evidenced, with fail-closed behavior validated before promotion docs are advanced. | Orchestrator fragmentation (multiple competing paths), missing fail-fast assertions, or fail-open behavior appears in CI/validator evidence. | **Contract owner** rolls back maturity claims/changelog entries to the last proven contract state. |
| Sprint 3 | Status/handoff operational artifacts are shipped and consumed (roadmap + sprint plan + sprint handoff show mirrored, evidence-backed transitions). | Required operational artifacts are missing, stale, or not consumed by downstream governance review (promotion parity check fails). | **Release/governance owner** blocks merge and reverts governance promotion synchronization until artifact consumption is restored. |

These criteria reuse the existing handoff ownership structure above and are mandatory promotion gates for sprint-level status advancement.

## Usage notes

- `docs/dod_manifest.json` remains the machine-readable source of capability status and test commands.
- This document defines when those capabilities are considered complete at capability, integration, and system layers.
- `docs/system_contract_map.md` remains the source of truth for contract maturity and changelog evidence.
- Contributor command workflow remains canonical in `README.md` and `docs/DEVELOPMENT.md`; use `make verify-dev-setup`, `make qa-commit`, `make qa-push`, and `make promotion-checks` before merge.

## Research note: weaker definition of done

The team acknowledges a weaker interim definition of done for research tracking:

- The system can deliver its own documentation artifacts.
- Drift detection is active and surfaces merge-conflict-producing divergence early.
- This state is useful for research/learning loops, but it is **not** sufficient to claim full completion against the completion layers and gates above.

Any sprint or milestone closing on this weaker condition must explicitly label it as research-only and include a follow-up plan to satisfy the full Definition of Complete gates.

_Last regenerated from manifest: 2026-03-03T00:00:00Z (UTC)._
