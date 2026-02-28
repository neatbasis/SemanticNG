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
