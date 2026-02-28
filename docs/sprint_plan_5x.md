# Sprint Plan 5x

This document defines a five-sprint execution plan that extends the current roadmap with explicit capability-ID exits, contract-map maturity transitions, and manifest-aligned pytest command packs.

Canonical references:
- Capability status and pytest command packs: `docs/dod_manifest.json`.
- Contract maturity transitions: `docs/system_contract_map.md`.
- Completion-layer criteria: `docs/definition_of_complete.md`.

## Governance outcomes to implement across this plan

The sprint plan below is constrained to deliver these governance outcomes by Sprint 5:

1. Machine-enforced sprint exit criteria and capability maturity entry/exit gates.
2. A no-regression budget policy for `done` capabilities.
3. Mandatory dependency impact statements in all PRs.
4. Timeboxed rollback plans for all exception paths.
5. Documentation freshness SLOs with CI-visible checks.
6. Sprint handoff artifact minimums.

## Sprint goals and exit criteria

### Sprint 1 — Documentation consolidation and governance baseline cleanup (source-of-truth alignment)

**Goal**
- Consolidate planning/governance documentation so capability status, ownership, and command-pack evidence remain synchronized across canonical docs.

**Exit criteria**
- Manifest capability alignment:
  - `capability_invocation_governance` remains explicitly tracked as current non-done governance target in planning docs.
  - `repair_aware_projection_evolution` remains dependency-gated behind governance + replay readiness.
- Contract-map maturity transition:
  - No forced maturity promotion; only consistency pass confirming existing maturity labels (`operational` / `proven`) and changelog format validity in `docs/system_contract_map.md`.
- Required pytest command packs:
  - `pytest tests/test_validate_milestone_docs.py tests/test_dod_manifest.py tests/test_capability_parity_report.py tests/test_governance_doc_parity.py`
- Governance policy artifacts:
  - Author and approve a no-regression budget policy for all `done` capabilities (including allowed waiver window + required owner).
  - Define documentation freshness SLO thresholds and the exact governed docs list.
  - Publish sprint handoff artifact minimum template used in Sprint 2+ reviews.

### Sprint 2 — Capability invocation governance implementation and test hardening

**Goal**
- Implement and harden policy-aware capability invocation governance so unauthorized or unpredicted external actions fail closed with auditable halts.

**Exit criteria**
- Manifest capability alignment:
  - `capability_invocation_governance` promoted from `planned` -> `in_progress` (implementation start) and then `in_progress` -> `done` only when all listed packs are green and evidence links are recorded.
  - Dependencies remain explicit: `observer_authorization_contract`, `invariant_matrix_coverage`, `channel_agnostic_pending_obligation`.
- Contract-map maturity transition:
  - `Observer authorization contract`: `operational` -> `proven` once governance-path regressions repeatedly validate authorization-gated invocation behavior.
  - `Channel-agnostic decision/effect contract`: `operational` -> `proven` once policy-aware effect gating is stable under governance suites.
- Required pytest command packs:
  - `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py tests/test_predictions_contracts_and_gates.py`
  - `pytest tests/test_capability_adapter_surface_policy_guards.py tests/test_observer_frame.py tests/test_invariants.py`
- Governance control implementation:
  - Implement machine-enforced capability maturity transition checks (`planned` -> `in_progress` -> `done`) in CI validation scripts.
  - Require mandatory dependency impact statements in PRs via template + validator checks.
  - Require timeboxed rollback plans for every governance exception path (including explicit rollback date and accountable owner).

### Sprint 3 — Repair-aware projection evolution (auditable repair events + replay guarantees)

**Goal**
- Evolve repair mode to emit auditable repair events with deterministic replay/restart guarantees and no silent mutation.

**Exit criteria**
- Manifest capability alignment:
  - `repair_aware_projection_evolution` promoted from `planned` -> `in_progress` at sprint start, and to `done` only after repair lineage and replay guarantee evidence are complete.
  - `capability_invocation_governance` remains `done` and non-regression-gated while repair evolution lands.
- Contract-map maturity transition:
  - `Replay projection analytics contract`: `operational` -> `proven` after repair-event replay/restart determinism is repeatedly validated.
  - `Projection view contract`: `operational` -> `proven` after repair events are represented without breaking projection determinism.
- Required pytest command packs:
  - `pytest tests/test_repair_mode_projection.py tests/test_repair_events_auditability.py`
  - `pytest tests/test_replay_projection_analytics.py tests/test_replay_projection_determinism.py tests/test_replay_projection_restart_contracts.py tests/replay_projection_analytics/test_append_only_replay.py`
  - `pytest tests/test_predictions_contracts_and_gates.py`
- Governance control implementation:
  - Enforce no-regression budget policy in CI for all `done` capability command packs.
  - Enforce documentation freshness SLO checks in CI for governed docs.
  - Require sprint handoff artifact minimum set on each sprint-close PR.

### Sprint 4 — Coherent refactor pass (module boundaries, adapter contracts, dead-path removal, naming normalization) with no behavior regressions

**Goal**
- Execute a coherence refactor that improves boundaries and naming while preserving runtime behavior and governance guarantees.

**Exit criteria**
- Manifest capability alignment:
  - No capability status regressions (`done` capabilities remain `done`; no implicit reopening without explicit roadmap + manifest edits).
  - `contract_map_refs` for touched capabilities remain accurate after module/path normalization.
- Contract-map maturity transition:
  - No maturity downgrade permitted.
  - Any promoted contract must include changelog evidence URL and repeated regression pass coverage.
- Required pytest command packs:
  - `pytest tests/test_predictions_contracts_and_gates.py tests/test_engine_projection_mission_loop.py tests/test_contracts_halt_record.py tests/test_persistence_jsonl.py`
  - `pytest tests/test_capability_invocation_governance.py tests/test_capability_adapter_policy_guards.py tests/test_capability_adapter_surface_policy_guards.py`
  - `pytest tests/test_replay_projection_analytics.py tests/test_replay_projection_determinism.py tests/test_repair_events_auditability.py`
- Governance control implementation:
  - Verify all machine-enforced gates remain green after refactor (maturity transitions, regression budget, dependency impact and rollback sections, freshness SLO, sprint handoff artifacts).
  - Resolve all temporary governance waivers or re-file with updated rollback deadlines approved for Sprint 5 only.

### Sprint 5 — Strategic documentation of capabilities worth developing and capabilities required to support them (dependency graph + maturity pathways)

**Goal**
- Publish a forward strategy for new capabilities, explicitly separating target outcomes from reusable enabling capabilities and defining maturity pathways.

**Exit criteria**
- Manifest capability alignment:
  - New planned capabilities (if introduced) are added to `docs/dod_manifest.json` with prerequisites, `contract_map_refs`, and initial command packs.
  - Existing capability IDs are referenced consistently across roadmap, manifest, and contract map.
- Contract-map maturity transition:
  - Each newly proposed capability maps to at least one existing contract (or proposes a new contract row with initial maturity target `prototype`).
  - Promotion pathways (`prototype` -> `operational` -> `proven`) documented for each proposed contract-capability pairing.
- Required pytest command packs:
  - `pytest tests/test_dod_manifest.py tests/test_capability_parity_report.py tests/test_validate_milestone_docs.py`
  - `pytest tests/test_governance_doc_parity.py tests/test_pr_template_autogen_governance.py tests/test_governance_pr_evidence_validator.py`
- Governance control implementation:
  - Publish a maturity-gate operations guide explaining how entry/exit gates, no-regression budget policy, and rollback plans are administered.
  - Publish freshness SLO trend report for the full five-sprint window.
  - Publish sprint handoff archive index proving artifact minimums were met for each sprint.

## Machine-enforced gate design (delivery blueprint)

Use this as the implementation contract for CI/governance scripts during Sprints 2-4.

### Capability maturity entry/exit gates

- Entry gate (`planned` -> `in_progress`):
  - Dependency capabilities listed as prerequisites must be `done`.
  - Command packs for target capability must exist in `docs/dod_manifest.json`.
- Exit gate (`in_progress` -> `done`):
  - All target capability command packs are green and have evidence URLs.
  - Contract map maturity changes (if any) include changelog evidence links.

### No-regression budget policy

- `done` capabilities have a zero-fail budget on canonical command packs.
- Any temporary waiver must include owner, reason, and rollback-by sprint/date.
- Waivers auto-expire at the next sprint-close unless renewed with explicit approval.

### PR governance requirements

- Every PR must include:
  - dependency impact statement,
  - regression budget impact declaration,
  - rollback plan (or explicit `not_applicable` reason).

### Documentation freshness SLO

- Governed docs must contain `Last regenerated` (or equivalent) metadata.
- SLO threshold breach is CI-failing for milestone/governance PRs.

### Sprint handoff artifact minimums

- Required sprint-close artifacts:
  - exit-criteria pass/fail table,
  - open-risk register with owners and target dates,
  - next-sprint preload list mapped to capability IDs.

## Supporting capability leverage table

Required capabilities below are listed as reusable platform investments, each with broader multi-context benefits beyond single-use dependencies.

| Required capability ID | Primary role in this plan | Broader benefit 1 (reusable) | Broader benefit 2 (reusable) |
| --- | --- | --- | --- |
| `observer_authorization_contract` | Policy envelope for capability invocation gating. | Enables scoped sandboxing for future external adapters and tool integrations. | Standardizes audit-ready authorization context for CI evidence and incident reviews. |
| `invariant_matrix_coverage` | Regression safety net across gate paths. | Improves change confidence during refactors by preserving deterministic stop semantics. | Provides reusable failure taxonomy (`invariant_id`) for planning prioritization and SLO tracking. |
| `channel_agnostic_pending_obligation` | Stable decision/effect carrier for governance checks. | Supports multi-channel interface growth without reworking core decision contracts. | Enables consistent pending-obligation analytics across adapters and replay consumers. |
| `replay_projection_analytics` | Deterministic replay/restart foundation for repair evolution. | Enables post-incident forensic reconstruction without runtime side channels. | Supports longitudinal quality analytics and correction-cost attribution for roadmap decisions. |
| `gate_halt_unification` | Shared fail-closed control plane for governance + repair. | Keeps explainability payloads stable for compliance-facing evidence exports. | Reduces integration risk by centralizing stop-path semantics across modules. |

## Future planned capabilities register

Use this register when introducing additional `planned` capability IDs.

| Capability ID (proposed) | Intent | Enabling prerequisites (capability IDs) | Reusable support value | Maturity target | Evidence needed for promotion |
| --- | --- | --- | --- | --- | --- |
| `capability_dependency_graph_service` | Provide machine-readable dependency graph generation for roadmap/manifest synchronization. | `capability_invocation_governance`, `invariant_matrix_coverage` | Reusable planning graph for prioritization, blast-radius analysis, and onboarding. | `operational` | Graph generation tests + parity checks proving manifest/roadmap/contract-map consistency in CI. |
| `repair_policy_simulation_harness` | Simulate policy outcomes for repair proposals before runtime activation. | `repair_aware_projection_evolution`, `observer_authorization_contract`, `replay_projection_analytics` | Reusable what-if analysis for policy tuning and incident rehearsal. | `prototype` -> `operational` | Deterministic simulation fixtures, replay equivalence assertions, and governance guard regression packs. |
| `cross_capability_evidence_orchestrator` | Automate capability-level evidence assembly for promotion PRs and release gates. | `capability_dependency_graph_service`, `invariant_matrix_coverage` | Reusable compliance/reporting backbone for all maturity transitions, not just one feature. | `operational` | End-to-end evidence rendering tests, URL integrity checks, and manifest command-pack extraction validation. |

## Dependency and maturity pathway notes

- Capability promotion must always be synchronized across:
  1. `docs/dod_manifest.json` status + pytest command packs,
  2. `ROADMAP.md` status alignment,
  3. `docs/system_contract_map.md` maturity rows/changelog,
  4. Promotion workflow checklist items in `README.md`.
- A capability cannot be promoted to `done` unless its required command packs pass and its contract maturity transition rationale is recorded.
