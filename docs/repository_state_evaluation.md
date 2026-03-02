# Repository state evaluation: invariant registry and halt-evidence provenance

Date: 2026-03-02 (updated to current source snapshot)

## Scope

This update is based on the current implementations and tests in:

- `src/state_renormalization/invariants.py` (specifically `InvariantId.AUTHORIZATION_SCOPE` and `check_authorization_scope`).
- `tests/test_invariants.py`.
- `tests/test_predictions_contracts_and_gates.py` (halt evidence reference assertions).

## Executive summary

The previously reported gaps around authorization registry coverage and `halt_evidence_ref` provenance are no longer present in the current codebase.

1. **Authorization scope is now first-class in the invariant system.** `authorization.scope.v1` is defined in `InvariantId`, implemented via `check_authorization_scope`, and included in both `REGISTRY` and branch-behavior metadata.
2. **Authorization pass/stop behavior is covered by invariant tests.** Unit tests assert deterministic pass/fail shape and normalized output for `check_authorization_scope`.
3. **Halt evidence provenance is explicitly codified and verified.** Engine behavior documents canonical provenance, and integration tests assert that emitted `halt_evidence_ref` values match the persisted halt row for invariant halts, authorization halts, and policy denials.

## Current findings

### 1) Authorization invariant registry alignment is resolved

- `InvariantId` includes `AUTHORIZATION_SCOPE = "authorization.scope.v1"`.
- `check_authorization_scope` is implemented with three explicit paths:
  - non-applicable (`authorization_allowed is None`) → continue,
  - authorized → continue,
  - unauthorized → stop with evidence and remediation hint.
- `REGISTRY` registers `InvariantId.AUTHORIZATION_SCOPE`.
- `REGISTERED_INVARIANT_BRANCH_BEHAVIORS` includes explicit continue/stop contracts for authorization scope.

**Assessment:** No active remediation required for authorization-registry absence; this issue is closed.

### 2) Halt evidence reference semantics are implemented and test-backed

- Engine helper `_persist_halt_and_get_evidence_ref(...)` now includes a canonical provenance contract comment stating that authorization halts, invariant halts, and policy-denial halts source `halt_evidence_ref` from the persisted halt row.
- Tests verify this behavior end-to-end:
  - `test_halt_artifact_includes_halt_evidence_ref_and_invariant_context`
  - `test_invariant_halt_evidence_ref_matches_persisted_halt_row`
  - `test_authorization_halt_evidence_ref_matches_persisted_halt_row`
  - `test_policy_denial_halt_evidence_ref_matches_persisted_halt_row`

**Assessment:** The prior TODO-style concern around unresolved `halt_evidence_ref` semantics is no longer accurate; behavior is now specified and enforced by assertions.

## Recommendations (current-state based)

1. **Keep the existing coverage guardrails in place.** Continue treating authorization and halt provenance checks as release-gating regression tests.
2. **Optionally add a focused non-applicable authorization test.** Current tests cover pass/stop explicitly; adding a dedicated `authorization_allowed=None` assertion in `tests/test_invariants.py` would make all three authorization branches explicit at the unit level.
3. **Maintain comment-to-test parity.** If `_persist_halt_and_get_evidence_ref` provenance rules change, update the related halt evidence tests in the same change set.

## Conclusion

The sections that previously described (a) authorization invariant registry absence and (b) unresolved engine TODO semantics around `halt_evidence_ref` should be considered superseded by current code and tests.
