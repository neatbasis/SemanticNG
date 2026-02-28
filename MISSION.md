# Mission

SemanticNG exists to make consequential system behavior predict-first, evidence-grounded, contract-bounded, and replayable so decisions remain safe, auditable, and continuously improvable over time.

The normative architecture/planning axiom set that operationalizes this north star lives in `docs/AXIOMS.md` and should be treated as the boundary for design changes.

## North-Star Principles (current enforcement targets)

1. **Prediction precedes action (`engine.py` + `invariants.py`)**  
   Every state-changing or externally consequential step must be gated by invariant checks and tied to a durable `PredictionRecord` before execution proceeds.

2. **Evidence anchors every claim (`contracts.py`)**  
   Values asserted by the system should carry explicit evidence/derivation references or be marked as unknown/pending; contract shapes are the minimum bar for expressing those claims.

3. **Contracts define capability boundaries (`contracts.py` + `engine.py`)**  
   Capability inputs/outputs are valid only when they satisfy explicit contract schemas; shape and validation precede interpretation and execution.

4. **Decisions must be explainable post-hoc (`invariants.py` + `engine.py`)**  
   Gate failures and halts must emit structured, machine-readable records (for example `HaltRecord`) that identify violated invariants and minimal recovery context.

5. **Behavior is defined by executable specification (`tests/` + `src/features/`)**  
   Invariants and critical control-flow guarantees are treated as behavior contracts and locked through automated tests, not informal intent.

## Current-Phase Non-Goals

- Building autonomous self-repair loops that silently mutate state to satisfy invariants.
- Optimizing for throughput/latency ahead of determinism, auditability, and correctness.
- Expanding broad capability coverage before the prediction/evidence/halt substrate is hardened.
- Treating mutable in-memory state as source of truth instead of append-only records + deterministic projection.
- Using opaque heuristics where contract validation or invariant checks should decide behavior.
