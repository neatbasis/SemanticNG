# Project Maturity Evaluation (2026-02-28)

## Executive assessment

SemanticNG is in an **early operational maturity** state:

- Core baseline capabilities are implemented and tested (`3/5` manifest capabilities are `done`).
- The entire current pytest suite is passing locally.
- The architecture has clear milestone framing (`Now` / `Next` / `Later`) and contract-level maturity tracking.
- The most critical unfinished work is concentrated in gate/halt unification and durable halt replay behavior.

## Evidence snapshot

### Capability delivery status (from DoD manifest)

- **Done:** 3
- **In progress:** 1
- **Planned:** 1

Completion ratio (done / total): **60%**.

This indicates the project is beyond prototype discovery, but not yet at system hardening completeness.

### Quality and validation signals

- Test suite currently passes (`pytest -q`).
- Roadmap items are linked to concrete test commands.
- Contract map defines explicit maturity labels (`prototype`, `operational`, `proven`) and promotion protocol.

### Lifecycle/process signals

- Repository documents a clear document lifecycle and milestone structure.
- Recent commit history shows active iteration on invariants, halts, observer authorization, schema selection, and contract mapping.

## Maturity conclusion

**Current stage: Operational foundation / pre-hardening**

The project has:

- Strong foundational contracts and deterministic behavior coverage.
- A disciplined test-driven roadmap.
- Active evolution in governance and halt semantics.

It does **not yet** have:

- Fully unified gate/halt behavior persisted and replay-validated across all invariant branches.
- Replay-grade longitudinal analytics maturity.

## Most timely development (priority recommendation)

### #1 Immediate priority

**Finish `gate_halt_unification` (Next milestone) before expanding Later capabilities.**

Why this is most timely:

1. It is the only capability already marked `in_progress` in the DoD manifest.
2. It directly de-risks runtime safety by ensuring every STOP path is explainable and durably persisted.
3. It is a prerequisite stabilizer for replay analytics and governance-heavy future features.

### #2 Concrete near-term execution sequence

1. **Complete unified gate pipeline parity**
   - Ensure pre-consume and post-write invariant checks behave consistently for both `Flow.CONTINUE` and `Flow.STOP`.
2. **Enforce durable explainable halts**
   - Verify persisted halt records always include invariant identity, details, and evidence.
3. **Close invariant matrix gaps**
   - Parameterize tests so every registered invariant deterministically covers pass/stop paths.

### #3 Defer until #1 is green

- Replay-grade projection/correction analytics.
- Larger external capability governance surface expansion.

## Suggested maturity targets for next review

- Promote halt normalization from `prototype` to `operational` after durable halt persistence assertions are complete.
- Keep a changelog note in `docs/system_contract_map.md` for any maturity promotion.
- Recompute capability completion and confirm all `Next` tests pass in CI before prioritizing `Later` features.

## Next milestone checkpoints

| Next milestone | Target date | Owner area | Pass criteria |
| --- | --- | --- | --- |
| Unified gate pipeline parity | 2026-03-15 | Engine + Invariants | `tests/test_predictions_contracts_and_gates.py` is green with explicit `Flow.CONTINUE` and `Flow.STOP` assertions for core gate scenarios. |
| Durable explainable halt persistence | 2026-03-22 | Invariants + Contracts + Persistence | `tests/test_predictions_contracts_and_gates.py` and `tests/test_persistence_jsonl.py` are green with halt `details`, `evidence`, and invariant identity persisted/replayable. |
| Invariant matrix completion | 2026-03-29 | Invariants + Test harness | `tests/test_predictions_contracts_and_gates.py` is green with parameterized coverage across all registered `InvariantId` pass/stop branches. |
