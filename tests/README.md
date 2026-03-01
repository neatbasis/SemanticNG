# Type-checking expectations for contributors

Type-checking is split into two tiers so local hooks stay fast while CI keeps broad coverage:

- **Tier 1 (pre-commit):** strict checks for `src/state_renormalization` and `src/core`.
- **Tier 2 (CI full surface):** `mypy --config-file=pyproject.toml src tests`.

When changing tests or BDD-related code, run the Tier 2 command locally before pushing so your local checks match CI scope.

```bash
mypy --config-file=pyproject.toml src tests
```

---

# Test setup conventions

Use shared fixtures from `tests/conftest.py` for recurring contract objects:

- `make_policy_decision(...)`
- `make_ask_result(...)`
- `make_episode(...)`
- `make_observation(...)`
- `make_schema_selection(...)`

## Fixture vs inline helper

- **Use shared fixtures/factories** when constructing common domain objects (`Episode`, `AskResult`, schema selection inputs) that appear in multiple test modules.
- **Use inline helpers** only when setup is truly scenario-specific and would make a shared fixture less readable (for example, one-off malformed payloads or highly custom monkeypatch behavior).
- Prefer composing shared fixtures in the test body over creating private `_mk_*` helpers in individual files.

## Behave step setup

For step definitions under `src/features/steps/`, keep step functions thin and move reusable scenario setup logic into clearly named helper functions in the same module.

## Invariant matrix maintenance

- Keep `INVARIANT_RELEASE_GATE_MATRIX` in `tests/test_predictions_contracts_and_gates.py` in sync with `InvariantId`/`REGISTRY`.
- For each newly added invariant, add deterministic `pass` and `stop` scenarios when the checker can meaningfully return both outcomes.
- If an invariant is not directly evaluated by `evaluate_invariant_gates`, keep `gate_inputs=None` in its scenarios and still assert checker/normalization contracts.
- If an invariant is gate-evaluated, provide `gate_inputs` so artifact-contract assertions exercise both prediction and halt branches.

### Extension guide for new invariants

When adding a new invariant checker in `src/state_renormalization/invariants.py`:

1. Add an `INVARIANT_RELEASE_GATE_MATRIX` entry in `tests/test_predictions_contracts_and_gates.py` keyed by the new `InvariantId`.
2. Add at least one admissible (`Flow.CONTINUE`) scenario and ensure it is deterministic.
3. If the checker can emit `Flow.STOP`, add a stop scenario and include representative `gate_inputs` when it is exercised by `evaluate_invariant_gates`.
4. Keep the expected ordered tuple in `test_invariant_identifiers_are_enumerated_and_registered` updated with the new invariant ID string and ensure `REGISTERED_INVARIANT_IDS` in `src/state_renormalization/invariants.py` remains the source of truth.
5. Keep matrix scenario names explicit as `pass` and `stop`; `test_invariant_matrix_has_explicit_pass_stop_scenarios_per_invariant` is the guard that enforces this contract.
6. Run the invariant contract tests; the guard test `test_invariant_matrix_guard_fails_when_registry_gains_uncovered_invariant` should fail if matrix coverage is incomplete.
