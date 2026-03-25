# Purpose Maturity Audit (Repository-Evidence Only)

_Date: 2026-03-25 (UTC)_

## 1. Executive summary

SemanticNG currently presents as a **governance-heavy, contract-oriented Python substrate** for “state renormalization” workflows (prediction records, invariant-gated mission loop execution, append-only persistence, and deterministic replay analytics), rather than a newcomer-ready end-user product.

The implementation is real and test-backed in core areas (engine/contracts/persistence/status tooling), but discovery is burdened by dense process documentation and limited runnable “hello world” pathways.

The strongest executable truth is in unit/integration tests and developer scripts; there is no obvious packaged CLI/app entrypoint that demonstrates user-facing value in one command.

## 2. Stated vs implemented purpose

### Stated purpose
- README states focus on “state renormalization, schema selection, and behavior-driven test scenarios.”
- Mission states predict-first, evidence-grounded, contract-bounded, replayable behavior.
- Roadmap claims broad “Now” capabilities are implemented and verified by named test packs.

### Implemented purpose
- `engine.py` provides an executable mission loop (`run_mission_loop`) that emits/persists prediction artifacts and applies invariant/adapter orchestration.
- `contracts.py` defines typed contracts for prediction, projection, belief, and halt semantics.
- `adapters/persistence.py` provides append-only JSONL persistence primitives and evidence refs.
- `engine.py` also provides replay analytics (`replay_projection_analytics`) over persisted event streams.
- `scripts/dev/status_report.py` provides a runnable status consistency check.

### Demonstrated use
- Tests explicitly execute mission loop behavior and validate persisted prediction logs (`tests/test_demo_runner.py`).
- Additional targeted tests run and pass for mission-loop/projection/status-report paths.
- `bootstrap_preflight.py` and `status_report.py status-check` execute successfully in this environment.

### Aspirational claims (or claims needing caution)
- Roadmap and manifest characterize many capabilities as `done`, but repository-level `pytest -q` currently fails due to a manifest canonical-field mismatch expectation in `tests/test_capability_parity_report.py`.
- This gap lowers confidence in “all-green governance reality” versus documented maturity posture.

## 3. Best-supported use cases

1. **Contract-first experimentation with mission-loop state transitions**
   - Create `Episode` + `BeliefState` + `ProjectionState`, run `run_mission_loop`, inspect artifacts/prediction log.
2. **Append-only prediction/halt event persistence and replay-style projection analytics**
   - Use persistence adapter functions plus `replay_projection_analytics`.
3. **Governance/status integrity checks for internal process enforcement**
   - Run status and quality gate helper scripts.
4. **Test-driven extension/refactoring of orchestration contracts**
   - Strong test surface around contracts, invariants, adapters, and policy guardrails.

## 4. Evidence inventory

### Documentation evidence
- `README.md` mission framing, quality gates, and setup workflow.
- `MISSION.md` explicit north-star and non-goals.
- `ROADMAP.md` “Now/Next/Later” capability and test-claim mapping.
- `docs/README.md` documentation topology and source-of-truth hierarchy.
- `docs/dod_manifest.json` capability status + pytest command inventory.

### Code evidence
- `src/state_renormalization/engine.py` mission loop and replay analytics functions.
- `src/state_renormalization/contracts.py` contract classes (`PredictionRecord`, `ProjectionState`, `BeliefState`).
- `src/state_renormalization/adapters/persistence.py` append/read JSONL evidence pipeline.
- `src/semanticng/__init__.py` package namespace behavior (re-export), indicating library orientation.

### Executable evidence collected in this audit
- `pytest -q` (failed: canonical source-of-truth assertion mismatch).
- `pytest -q tests/test_demo_runner.py tests/test_engine_projection_mission_loop.py tests/test_status_report.py` (passed).
- `python scripts/dev/bootstrap_preflight.py` (passed).
- `python scripts/dev/status_report.py status-check` (passed).

## 5. Reasoning clarity assessment

- **Strengths:** Mission vocabulary is explicit; architecture and governance intent are over-documented and traceable.
- **Weaknesses:** The repo foregrounds governance/process more than practical usage narrative; newcomers must infer “what this does” by synthesizing many docs.
- **Net:** High internal traceability, moderate external comprehensibility.

## 6. Example/trialability assessment

- There is no obvious top-level “run this to see value” example script in README akin a single executable demo command.
- Trialability currently depends on reading tests and constructing objects manually or running slices of pytest.
- BDD features exist, but newcomer path from clone to outcome is not presented as a cohesive trial recipe.

## 7. Proof/trust assessment

- Positive: broad automated test inventory and script-based guardrails indicate active validation infrastructure.
- Negative: full `pytest -q` failed in this snapshot, signaling drift between governance assertions and canonical manifest content.
- Trust posture: moderate; strong local proof fragments, but one failing global contract check undermines “fully coherent, always-green” confidence.

## 8. Maturity strengths

- Contract-centric core with typed models and explicit boundaries.
- Deterministic persistence + replay-oriented analytics primitives.
- Evidence-oriented governance structure (manifest, status docs, CI command packs).
- Dense test coverage across many policy/contract surfaces.

## 9. Maturity gaps

- **Purpose discoverability gap:** user outcomes are not immediately legible from top-level docs.
- **Entrypoint gap:** no canonical runnable “product demo” command.
- **Proof coherence gap:** at least one repo-wide test currently fails in baseline run.
- **Signal-to-noise gap:** heavy governance language can obscure practical operational capability.

## 10. Smallest high-leverage improvements

1. Add a **single-file runnable demo** (e.g., `examples/mission_loop_smoke.py`) and link it near top of README.
2. Add a **“What you can do today”** section in README with 3 concrete scenarios and exact commands.
3. Keep one **minimal green acceptance command** as default newcomer proof (e.g., `make smoke`), mapped to stable test subset.
4. Resolve parity mismatch causing current `pytest -q` failure (manifest canonical-field expectation drift).
5. Add a concise **library API entrypoint map** (`run_mission_loop`, persistence append/read, replay) for first-time adopters.

## 11. Final verdict (0–3)

- purpose clarity: **2/3**
- scope clarity: **2/3**
- structural coherence: **2/3**
- entry-point clarity: **1/3**
- example quality: **1/3**
- setup reproducibility: **2/3**
- proof via tests/CI: **2/3**
- contract explicitness: **3/3**
- newcomer trialability: **1/3**

Overall: **usable as a contract-governed engineering substrate now**, but **not yet newcomer-optimized as an easily trialable product**.
