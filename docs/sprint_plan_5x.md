# Sprint Plan 5x

This document defines a five-sprint execution plan with explicit capability-ID scope, measurable exits, and parity gates across:

- `ROADMAP.md`
- `docs/dod_manifest.json`
- `docs/system_contract_map.md`

Canonical references:
- Capability status and pytest command packs: `docs/dod_manifest.json`.
- Contract maturity transitions: `docs/system_contract_map.md`.
- Completion-layer criteria: `docs/definition_of_complete.md`.
- Coverage threshold governance policy: `docs/release_checklist.md` (Coverage threshold governance policy section).

## Sprint-close artifact evidence requirement

- [ ] Sprint-close checklist includes coverage artifact evidence for the closing sprint (link to CI artifact or attached report summary), including enough detail to validate governance decisions.

## Source-of-truth matrix

| Decision type | Canonical source-of-truth | One-way derivation rule |
| --- | --- | --- |
| Capability status | `docs/dod_manifest.json` | `ROADMAP.md`, `docs/system_contract_map.md`, and sprint notes must reference capability IDs and mirror manifest state; they must not introduce independent status authority. |
| Maturity level | `docs/system_contract_map.md` | Maturity transitions must cite capability IDs from `docs/dod_manifest.json` and evidence links; downstream docs may summarize but not redefine maturity state. |
| Horizon sequencing | `ROADMAP.md` | Horizon notes derive from capability IDs and dependency map; execution docs consume this sequence without redefining horizon ownership. |
| Sprint execution controls | `docs/sprint_plan_5x.md` | Sprint controls (gates, PR requirements, templates) govern execution mechanics only and must reference capability IDs for scope. |

## Coverage scope roadmap

### Current scope baseline
- Coverage-governed execution scope is currently limited to `src/state_renormalization`.
- Sprint evidence, parity validators, and maturity claims must continue to map to this baseline until explicit scope-expansion readiness is accepted.

### Conditions required to include `src/core`
- Contract stability: canonical contract names and payload surfaces must remain stable across two consecutive sprint closes, with no unplanned schema churn in `docs/system_contract_map.md`.
- Deterministic tests: replay/projection and gate-path suites must show deterministic repeated runs for the candidate `src/core`-touching workflows.
- Parity gates: roadmap/manifest/contract-map parity validators must pass in fail-closed mode before and after any candidate scope update.

### Sequencing constraints tied to refactoring milestones
1. Keep scope at `src/state_renormalization` through refactor-only milestones where behavior drift is disallowed.
2. Allow `src/core` expansion only after the coherence/refactor milestone confirms naming/boundary cleanup with invariant freeze still green.
3. Execute first `src/core` inclusion as a gated, single-sprint rollout with rollback criteria, then widen only after one additional green sprint cycle.


## Current promotion-state ledger (manifest synchronized)

- `capability_invocation_governance`: `in_progress` (acceptance command pack is active in CI; retain `operational` contract maturity until completion evidence closes).
- `repair_aware_projection_evolution`: `planned` (sequenced after governance reaches `done`; no independent promotion is valid yet).

## Sprint 1 — Governance substrate lock

### Objective
Finalize no-regression budget, doc freshness SLO checks, handoff minimums, and parity validators so governance substrate controls are enforced before new capability promotions.

### Capability IDs in scope
- `capability_invocation_governance`
- `observer_authorization_contract`
- `invariant_matrix_coverage`
- `channel_agnostic_pending_obligation`

### Dependency assumptions
- Existing `done` dependencies remain green and non-regressing while governance substrate controls are introduced.
- No capability maturity promotion is allowed in this sprint unless parity validators and freshness SLO checks are already machine-enforced.

### Required pytest command packs (from `docs/dod_manifest.json`)
- `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py tests/test_predictions_contracts_and_gates.py`
- `pytest tests/test_observer_frame.py`
- `pytest tests/test_predictions_contracts_and_gates.py tests/test_invariants.py`
- `pytest tests/test_predictions_contracts_and_gates.py`
- `pytest tests/test_contracts_belief_state.py tests/test_contracts_decision_effect_shape.py tests/test_engine_pending_obligation.py tests/test_engine_pending_obligation_minimal.py`

### Maturity transition targets (from `docs/system_contract_map.md`)
- `Observer authorization contract`: hold at `operational` (readiness baseline only in this sprint).
- `Channel-agnostic decision/effect contract`: hold at `operational` (readiness baseline only in this sprint).
- `Projection view contract`: hold at `operational` under no-regression freeze.

### Measurable exits
- No-regression budget policy approved and referenced in CI checks for all `done` capabilities.
- Doc freshness SLO checks implemented for canonical governance docs.
- Handoff minimum template published and required in sprint-close artifacts.
- Parity validators fail closed on capability-ID mismatch across roadmap/manifest/contract map.

### Doc-alignment checkpoints
- Capability IDs and statuses in sprint notes exactly match `docs/dod_manifest.json`.
- Contract names used in sprint notes exactly match `docs/system_contract_map.md` names.
- `ROADMAP.md` sequencing references only manifest-defined IDs.

### Scope change readiness acceptance criterion
- [ ] Scope remains constrained to `src/state_renormalization`; any proposed `src/core` touch is deferred unless contract stability baseline, deterministic-test baseline, and parity-gate baseline are all documented as green.

### Alignment gate checklist (must pass before sprint close)
- [ ] `ROADMAP.md` capability IDs/statuses are parity-checked against `docs/dod_manifest.json`.
- [ ] `docs/dod_manifest.json` capability refs map to canonical contract names in `docs/system_contract_map.md`.
- [ ] `docs/system_contract_map.md` maturity statements referenced by this sprint are unchanged or explicitly changelogged.
- [ ] Governance artifacts (no-regression budget, SLO checks, handoff minimums) are linked in sprint close evidence.

## Sprint 2 — Capability invocation governance

### Objective
Advance `capability_invocation_governance` from its current `in_progress` state to `done` with policy-aware side-effect gate tests and explicit exception rollback controls.

### Capability IDs in scope
- `capability_invocation_governance`
- `observer_authorization_contract`
- `invariant_matrix_coverage`
- `channel_agnostic_pending_obligation`

### Dependency assumptions
- `observer_authorization_contract`, `invariant_matrix_coverage`, and `channel_agnostic_pending_obligation` remain `done` and green.
- Sprint 1 governance substrate controls are active in CI before promotion to `done`.

### Required pytest command packs (from `docs/dod_manifest.json`)
- `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py tests/test_predictions_contracts_and_gates.py`
- `pytest tests/test_observer_frame.py`
- `pytest tests/test_predictions_contracts_and_gates.py tests/test_invariants.py`
- `pytest tests/test_predictions_contracts_and_gates.py`
- `pytest tests/test_contracts_belief_state.py tests/test_contracts_decision_effect_shape.py tests/test_engine_pending_obligation.py tests/test_engine_pending_obligation_minimal.py`

### Maturity transition targets (from `docs/system_contract_map.md`)
- `Observer authorization contract`: `operational` -> `proven`.
- `Channel-agnostic decision/effect contract`: `operational` -> `proven`.
- `Projection view contract`: hold at `operational` unless replay/repair evidence also satisfies promotion protocol.

### Measurable exits
- `capability_invocation_governance` transitions `in_progress` -> `done` with linked evidence (the `planned` -> `in_progress` step is already recorded in `docs/dod_manifest.json`).
- Policy-aware side-effect gates fail closed for unauthorized invocations in CI suites.
- Dependency impact statements and timeboxed rollback plans are present in all sprint PRs.

### Doc-alignment checkpoints
- Manifest status for `capability_invocation_governance` is updated and mirrored in roadmap notes.
- Contract-map changelog entries exist for any maturity promotions.
- Policy gate test names in sprint evidence match manifest command packs exactly.

### Scope change readiness acceptance criterion
- [ ] Promotion evidence confirms contract stability and deterministic policy-gate behavior in current scope, and parity gates remain fail-closed as a prerequisite for future `src/core` inclusion.

### Alignment gate checklist (must pass before sprint close)
- [ ] `ROADMAP.md` reflects `capability_invocation_governance` final sprint state.
- [ ] `docs/dod_manifest.json` status and pytest packs are unchanged from executed evidence or updated in same PR.
- [ ] `docs/system_contract_map.md` maturity promotions include required changelog syntax and evidence URL.
- [ ] Parity validator reports zero drift across roadmap/manifest/contract map.

## Sprint 3 — Repair-aware projection evolution

### Objective
Deliver auditable repair events and deterministic replay/restart guarantees while preserving governance constraints from Sprint 2 once `capability_invocation_governance` reaches `done`.

### Capability IDs in scope
- `repair_aware_projection_evolution`
- `replay_projection_analytics`
- `capability_invocation_governance`

### Dependency assumptions
- `capability_invocation_governance` is `done` and enforced in CI.
- Replay analytics baseline remains stable enough to validate deterministic repair replay.

### Required pytest command packs (from `docs/dod_manifest.json`)
- `pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py`
- `pytest tests/test_predictions_contracts_and_gates.py`
- `pytest tests/test_predictions_contracts_and_gates.py tests/test_persistence_jsonl.py`
- `pytest tests/test_replay_projection_analytics.py tests/test_replay_projection_determinism.py tests/test_replay_projection_restart_contracts.py tests/test_prediction_outcome_binding.py`
- `pytest tests/replay_projection_analytics/test_append_only_replay.py`

### Maturity transition targets (from `docs/system_contract_map.md`)
- `Replay projection analytics contract`: `operational` -> `proven`.
- `Projection view contract`: `operational` -> `proven` (conditioned on deterministic replay/restart + repair-event audit evidence).

### Measurable exits
- `repair_aware_projection_evolution` remains `planned` until governance dependency closure, then transitions `planned` -> `in_progress` -> `done` with evidence links.
- Repair events are append-only, auditable, and replayable without silent mutation.
- Replay/restart determinism is repeated and documented across command packs.

### Doc-alignment checkpoints
- Manifest status transitions for `repair_aware_projection_evolution` are reflected in roadmap and sprint close notes.
- Contract-map maturity transitions include capability-ID references and evidence URLs.
- Repair/replay test evidence references exact command packs from manifest.

### Scope change readiness acceptance criterion
- [ ] Deterministic replay/restart evidence for repair/projection paths is repeatable and parity validated, establishing readiness evidence needed before any scope broadening beyond `src/state_renormalization`.

### Alignment gate checklist (must pass before sprint close)
- [ ] `ROADMAP.md` records repair-aware capability completion and dependency closure.
- [ ] `docs/dod_manifest.json` aligns with executed repair/replay command packs.
- [ ] `docs/system_contract_map.md` contains corresponding maturity changes and changelog entries.
- [ ] Parity validator reports no ID/name/status mismatch.

## Sprint 4 — Coherence refactor under invariant freeze

### Objective
Complete module boundary cleanup and naming normalization under invariant freeze with zero behavior drift.

### Capability IDs in scope
- `schema_selection_ambiguity_baseline`
- `channel_agnostic_pending_obligation`
- `gate_halt_unification`
- `invariant_matrix_coverage`

### Dependency assumptions
- Refactor work is constrained to structural and naming coherence only.
- Runtime behavior, invariant outcomes, and gate/halt semantics must remain unchanged.

### Required pytest command packs (from `docs/dod_manifest.json`)
- `pytest tests/test_schema_selector.py tests/test_schema_bubbling_option_a.py tests/test_capture_outcome_states.py tests/test_engine_calls_selector_with_generic_error.py`
- `pytest tests/test_contracts_belief_state.py tests/test_contracts_decision_effect_shape.py tests/test_engine_pending_obligation.py tests/test_engine_pending_obligation_minimal.py`
- `pytest tests/test_predictions_contracts_and_gates.py tests/test_engine_projection_mission_loop.py tests/test_persistence_jsonl.py tests/test_contracts_halt_record.py`
- `pytest tests/test_predictions_contracts_and_gates.py`

### Maturity transition targets (from `docs/system_contract_map.md`)
- `Ambiguity selection contract`: hold at `operational` unless repeated no-drift evidence supports promotion.
- `Pending-obligation belief contract`: hold at `operational` unless repeated no-drift evidence supports promotion.
- `Halt normalization contract`: hold at `proven` with strict no-regression budget enforcement.

### Measurable exits
- Refactor PRs demonstrate zero behavior drift through unchanged test outcomes and artifact parity.
- Naming normalization is completed with backward-compatible references and no contract-ID churn.
- Invariant freeze exceptions, if any, include timeboxed rollback plans.

### Doc-alignment checkpoints
- Contract names, invariants, and producing/consuming stage labels remain canonical in contract map.
- Manifest command packs remain authoritative and unchanged unless explicitly revised.
- Roadmap narrative reflects refactor-only scope without introducing new capability statuses.

### Scope change readiness acceptance criterion
- [ ] Refactor milestone closes with zero behavior drift, stable contracts, and deterministic suites, satisfying the sequencing prerequisite to consider a gated `src/core` pilot in a subsequent sprint.

### Alignment gate checklist (must pass before sprint close)
- [ ] `ROADMAP.md` indicates coherence/refactor scope with no unauthorized status changes.
- [ ] `docs/dod_manifest.json` capability IDs and command packs remain in parity with sprint evidence.
- [ ] `docs/system_contract_map.md` reflects no behavior drift and only approved naming updates.
- [ ] Parity validator confirms roadmap/manifest/contract map consistency.

## Sprint 5 — Proven-maturity hardening + release readiness

### Objective
Upgrade qualifying contracts from `operational` to `proven` using repeated evidence and close governance requirements for release readiness.

### Capability IDs in scope
- `capability_invocation_governance`
- `repair_aware_projection_evolution`
- `schema_selection_ambiguity_baseline`
- `channel_agnostic_pending_obligation`
- `replay_projection_analytics`

### Dependency assumptions
- Sprint 1–4 controls and no-regression budget checks are active and enforced.
- Candidate contracts for promotion have repeated green evidence across at least two sprint cycles.

### Required pytest command packs (from `docs/dod_manifest.json`)
- `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py tests/test_predictions_contracts_and_gates.py`
- `pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py`
- `pytest tests/test_predictions_contracts_and_gates.py`
- `pytest tests/test_schema_selector.py tests/test_schema_bubbling_option_a.py tests/test_capture_outcome_states.py tests/test_engine_calls_selector_with_generic_error.py`
- `pytest tests/test_contracts_belief_state.py tests/test_contracts_decision_effect_shape.py tests/test_engine_pending_obligation.py tests/test_engine_pending_obligation_minimal.py`
- `pytest tests/test_predictions_contracts_and_gates.py tests/test_persistence_jsonl.py`
- `pytest tests/test_replay_projection_analytics.py tests/test_replay_projection_determinism.py tests/test_replay_projection_restart_contracts.py tests/test_prediction_outcome_binding.py`
- `pytest tests/replay_projection_analytics/test_append_only_replay.py`

### Maturity transition targets (from `docs/system_contract_map.md`)
- `Projection view contract`: `operational` -> `proven` (if not promoted in Sprint 3, must be closed here).
- `Ambiguity selection contract`: `operational` -> `proven` (qualification-based).
- `Pending-obligation belief contract`: `operational` -> `proven` (qualification-based).
- `Channel-agnostic decision/effect contract`: ensure `proven` closure if not already complete in Sprint 2.
- `Observer authorization contract`: ensure `proven` closure if not already complete in Sprint 2.
- `Replay projection analytics contract`: ensure `proven` closure if not already complete in Sprint 3.

### Measurable exits
- All targeted contract promotions are changelogged with required syntax and evidence URLs.
- Governance closure package includes no-regression budget compliance report, freshness SLO report, and handoff artifact audit.
- Release readiness review signs off only after parity gate passes across roadmap/manifest/contract map.

### Doc-alignment checkpoints
- Final roadmap capability states exactly match manifest terminal states.
- Contract-map maturity table and changelog fully reflect promoted contracts.
- Manifest `contract_map_refs` remain canonical and complete for all active capabilities.

### Scope change readiness acceptance criterion
- [ ] Release-readiness package includes explicit sign-off on contract stability, deterministic test history, and parity-gate continuity as the acceptance gate for any approved post-plan scope expansion into `src/core`.

### Alignment gate checklist (must pass before sprint close)
- [ ] `ROADMAP.md` terminal statuses match `docs/dod_manifest.json` exactly.
- [ ] `docs/dod_manifest.json` pytest packs and contract refs align with executed evidence.
- [ ] `docs/system_contract_map.md` maturity values and changelog entries reflect all approved promotions.
- [ ] Governance closure artifacts are linked and auditable from sprint close notes.

## Forward-looking extension — Next five sprints (Sprints 6–10)

This extension proposes the next five sprint goals after the baseline 5x plan closes. It keeps the same governance pattern: capability-ID-first scope, manifest parity, contract-map maturity evidence, and fail-closed execution.

### Sprint 6 — Reliability hardening + CI signal quality

**Objective**
- Reduce flaky signal and improve confidence in existing `done` capabilities before opening larger surface expansion.

**Primary scope**
- Reliability pass across existing command packs in `docs/dod_manifest.json`.
- Stabilize deterministic replay/restart evidence collection and reporting.

**Measurable exits**
- Flaky-test rate trend is explicitly tracked for core command packs and reduced sprint-over-sprint.
- CI evidence artifacts include a compact reliability summary per capability ID.
- No maturity downgrades in `docs/system_contract_map.md`.

### Sprint 7 — Capability observability and decision explainability UX

**Objective**
- Improve operator-facing traceability for prediction/gate/halt decisions without changing contract semantics.

**Primary scope**
- Strengthen observability outputs from persisted lineage (prediction, decision/effect, halt, correction).
- Improve explainability documentation and evidence linkage in handoff artifacts.

**Measurable exits**
- Every sprint-close handoff includes capability-ID keyed decision traces.
- Replay lineage can be navigated from artifact to contract-map maturity entry with no missing links.
- Explainability output remains deterministic across repeated replay runs.

### Sprint 8 — Performance and scale envelope characterization

**Objective**
- Establish performance baselines and safe operating envelopes for replay/projection workflows.

**Primary scope**
- Introduce benchmark-style checks for append/read/replay workloads.
- Define capacity thresholds and alerting recommendations for growth scenarios.

**Measurable exits**
- Baseline throughput/latency numbers are documented with reproducible commands.
- Envelope limits and degradation modes are recorded with mitigation guidance.
- No contract regressions while performance checks are added.

### Sprint 9 — Integration-readiness and external adapter contract hardening

**Objective**
- Prepare interfaces for controlled external integrations while preserving strict fail-closed policy behavior.

**Primary scope**
- Harden adapter boundaries (`schema_selector`, `schemaorg_suggester`, `ask_outbox`, persistence edge behavior).
- Expand negative-path and policy-guard coverage for integration-facing contracts.

**Measurable exits**
- Adapter contract tests cover malformed input, timeout/error bubbling, and policy-denied paths.
- Integration notes provide explicit compatibility/rollback guidance.
- Governance parity validators continue to fail closed on ID/name/status mismatch.

### Sprint 10 — Release candidate validation and operational readiness

**Objective**
- Produce a release-candidate-quality validation package across governance, quality, reliability, and runtime readiness.

**Primary scope**
- Full command-pack sweep from `docs/dod_manifest.json` with release evidence collation.
- Final DoD/roadmap/contract-map parity confirmation and operational checklist sign-off.

**Measurable exits**
- Release evidence bundle includes test matrix, risk register, and rollback playbook.
- All canonical docs remain aligned (`ROADMAP.md`, `docs/dod_manifest.json`, `docs/system_contract_map.md`).
- Go/no-go decision is recorded with owner, date, and explicit unresolved risks.

### Cross-sprint controls for Sprints 6–10

- Continue weekly failure-concentration planning from `ROADMAP.md` as the default prioritization signal.
- Maintain no-regression budget enforcement and doc freshness SLOs as hard gates.
- Keep capability status authority in `docs/dod_manifest.json`; execution notes may summarize but not redefine status.
- Require sprint handoff artifacts to include evidence links for every claimed transition or closure.

### Canonical dependency statements (capability-ID only)

- `capability_invocation_governance` depends on: `observer_authorization_contract`, `invariant_matrix_coverage`, `channel_agnostic_pending_obligation`.
- `repair_aware_projection_evolution` depends on: `capability_invocation_governance`, `replay_projection_analytics`.
