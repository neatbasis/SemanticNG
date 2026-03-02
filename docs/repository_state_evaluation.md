# Repository state evaluation: mission, invariants, and milestone targets

Date: 2026-03-02

## Scope

This assessment compares current repository posture against:

- Mission principles (`MISSION.md`).
- Governance axioms (`docs/AXIOMS.md`).
- Invariant implementation and gate behavior (`src/state_renormalization/invariants.py`, `src/state_renormalization/engine.py`).
- Milestone and completion sources of truth (`docs/dod_manifest.json`, `ROADMAP.md`, `docs/system_contract_map.md`, `docs/definition_of_complete.md`).

## Executive summary

The repository demonstrates strong alignment on prediction-first gating, explainable halt shape, and replay-oriented architecture. However, four governance-relevant drifts remain:

1. **Capability-completion drift:** `invariant_matrix_coverage` is marked `done`, but branch-coverage audit still reports partial coverage with missing branch codes.
2. **Contract-boundary inconsistency:** `authorization.scope.v1` is treated as invariant-class governance in docs and runtime halts, but is not part of canonical invariant registry/checker lifecycle.
3. **Milestone metadata drift:** `docs/system_contract_map.md` changelog labels `invariant_matrix_coverage` transition as `(Next)` while current canonical status is `Now/done`.
4. **Explainability boundary ambiguity:** a TODO marker in engine halt artifact emission indicates unresolved provenance semantics for `halt_evidence_ref`.

## Detailed findings

### 1) Capability completion drift: invariant matrix coverage marked done while audit says partial

- `docs/dod_manifest.json` lists `invariant_matrix_coverage` as `done` in roadmap section `Now`.
- `docs/definition_of_complete.md` defines this capability as providing exhaustive branch assertions and non-applicable markers.
- `docs/invariant_gate_coverage_audit.md` still reports partial pass/stop status and missing branch codes across invariants.

**Impact:** Completion claims are stronger than current evidence, weakening mission principle that behavior is defined by executable specification and governance parity.

**Recommended remediation:** Either complete missing branch tests and refresh audit to full status, or downgrade capability status until coverage is complete.

### 2) Invariant contract-boundary inconsistency for authorization scope

- Governance map and contract map treat authorization scope (`authorization.scope.v1`) as invariant-bearing gate policy.
- Runtime emits authorization halts with `invariant_id="authorization.scope.v1"` in `engine.py`.
- Canonical invariant registry in `invariants.py` only includes four IDs and excludes `authorization.scope.v1`.

**Impact:** Authorization stop semantics bypass the shared checker registry lifecycle, making invariant coverage and branch-behavior guarantees less uniform.

**Recommended remediation:** Promote authorization scope into `InvariantId`, add registered checker + branch-behavior metadata, and route authorization gate outcomes through the same normalization/test harness used by other invariants.

### 3) Milestone/changelog metadata drift in contract-map evidence

- Current status sources align `invariant_matrix_coverage` with `Now` and `done`.
- `docs/system_contract_map.md` changelog records the transition entry under `(Next)`.

**Impact:** Documentation parity controls are undermined; milestone traceability becomes ambiguous across governance docs.

**Recommended remediation:** Update changelog milestone label and wording so it mirrors canonical manifest/roadmap status.

### 4) Incomplete explainability boundary around `halt_evidence_ref`

- `engine.py` contains a temporary TODO note in invariant artifact emission: `halt_evidence_ref` wiring was changed to pass precommit.

**Impact:** Indicates unresolved ownership/provenance semantics for halt evidence references; this conflicts with strict explainability and replay-grade auditability expectations.

**Recommended remediation:** Define canonical provenance rules per halt pathway (authorization, invariant gate stop, policy denial), remove temporary workaround comment, and add deterministic assertions in mission-loop/gate tests.

## Positive alignment noted

- Mission and axioms emphasize prediction-before-consequence, explainable halt payloads, deterministic replay, and contract-shape-first flow.
- Current invariant system enforces deterministic continue/stop structure and explicit branch behavior metadata.
- Manifest, roadmap, and sprint plan broadly align on `done` vs `planned` capabilities and dependency sequencing.

## Suggested follow-up task list

1. Add missing invariant branch tests identified by `docs/invariant_gate_coverage_audit.md` and re-evaluate `invariant_matrix_coverage` status.
2. Add first-class `authorization.scope.v1` checker to invariant registry and unify gate path handling.
3. Correct contract-map changelog milestone label for `invariant_matrix_coverage`.
4. Resolve and test canonical `halt_evidence_ref` provenance semantics.

