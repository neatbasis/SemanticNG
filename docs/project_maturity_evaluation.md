# Project Maturity Evaluation (2026-02-28)

## Executive assessment

SemanticNG is in an **operational hardening** state with replay completion achieved and remaining work concentrated in authorization-first governance expansion:

- Core baseline capabilities remain implemented and tested.
- Capability accounting from the manifest is now `6/9` done.
- Roadmap sequencing and contract-map maturity framing place the critical path on promoting observer authorization from `prototype` toward `operational` before `Later` governance scopes.

## Evidence snapshot

### Capability delivery status (from DoD manifest)

- **Done:** 6
- **In progress:** 0
- **Planned:** 3

Completion ratio (done / total): **66.7%** (`6/9`).

Current bottleneck capability (highest-priority non-`done`): **`observer_authorization_contract`**. It is the only `Next` item in the roadmap, remains `planned` in the manifest, and maps to a `prototype` maturity contract in `docs/system_contract_map.md`.

This indicates the project is beyond replay completion and is now in authorization hardening + governance sequencing.

### Quality and validation signals

- Test suite currently passes (`pytest -q`).
- Roadmap items are linked to concrete test commands.
- Contract map defines explicit maturity labels (`prototype`, `operational`, `proven`) and promotion protocol.
- Halt normalization and replay analytics validation packs are now part of regular milestone evidence.

### Lifecycle/process signals

- Repository documents a clear document lifecycle and milestone structure.
- Recent updates are concentrated on deterministic replay/restart behavior and governance sequencing.

## Maturity conclusion

**Current stage: Post-replay operational hardening / governance maturation**

The project has:

- Strong foundational contracts and deterministic behavior coverage.
- Replay-grade projection reconstruction and analytics validation coverage in active command packs.
- Hardened and explainable halt normalization behavior across unified gate paths.

It does **not yet** have:

- Observer authorization and capability-governance contracts promoted beyond planned/prototype stages.
- Full governance-path maturity across external capability invocation surfaces.

## Most timely development (priority recommendation)

### #1 Immediate priority

**Prioritize `observer_authorization_contract` as the single immediate implementation focus; queue `capability_invocation_governance` next once observer authorization is operational.**

Why this is most timely:

1. Replay projection analytics is marked `done` and sits in the `Now` milestone as a maintained non-regression baseline, not a delivery bottleneck.
2. The roadmap's `Next` section contains only observer authorization, making it the mandatory sequencing gate before `Later` governance capabilities.
3. The contract map shows observer authorization still at `prototype`, so maturity promotion here provides the largest near-term risk reduction.

### #2 Concrete near-term execution sequence

1. **Land runtime observer authorization enforcement (`Next`)**
   - Promote authorization checks from prototype-only contract framing to default-path runtime behavior with CI-backed gate coverage.
2. **Promote Observer authorization contract maturity**
   - Update contract-map maturity once tests show default runtime authorization and allowlist behavior are stable.
3. **Start capability governance implementation only after observer promotion (`Later`)**
   - Add deterministic tests for allowed/denied capability invocation outcomes after observer authorization enforcement is green.
4. **Keep replay/halt packs as non-regression gates**
   - Preserve replay/restart + halt explainability packs as required green checks while authorization/governance work lands.

### #3 Defer until #1 is green

- Repair-aware projection evolution.
- Any broad external integration surface expansion.

## Suggested maturity targets for next review

- Promote observer authorization from `prototype` toward `operational` with CI-backed default-path enforcement evidence.
- Establish `capability_invocation_governance` baseline test evidence only after observer authorization maturity promotion is recorded.
- Recompute capability completion and confirm observer + governance tests pass in CI before expanding repair-aware scope.

## Maturity changelog

- 2026-02-28: Sync pass — updated this evaluation to match manifest totals (`6 done / 0 in_progress / 3 planned`), roadmap sequencing (`observer_authorization_contract` as the sole `Next` item), and contract-map maturity framing (observer authorization still `prototype`); replay is treated as a maintained baseline rather than a bottleneck.
- 2026-02-28: Revalidated `gate_halt_unification` as `done` against its acceptance command (`pytest tests/test_predictions_contracts_and_gates.py tests/test_engine_projection_mission_loop.py tests/test_persistence_jsonl.py tests/test_contracts_halt_record.py` => `92 passed, 4 skipped`).
- 2026-02-28: Confirmed `tests/test_predictions_contracts_and_gates.py` enforces deterministic `Flow.CONTINUE`/`Flow.STOP` parity assertions and `tests/test_persistence_jsonl.py` verifies halt payload durability for canonical `details`, `evidence`, and invariant identity (`invariant_id`) round-trips.

## Maturity review protocol

Run a maturity review whenever one of these triggers occurs:

1. A capability status changes in `docs/dod_manifest.json` (especially `planned` → `in_progress` or `in_progress` → `done`).
2. A contract maturity level changes in `docs/system_contract_map.md` (`prototype`/`operational`/`proven`).
3. A milestone boundary is crossed (`Now`/`Next`/`Later`) or a milestone target date is reached.
4. A critical gate/halt or replay regression test command changes or starts failing.

For each review, execute this update sequence:

1. Recompute capability ratios directly from `docs/dod_manifest.json` and update this document with current `done`, `in_progress`, and `planned` totals.
2. Set the **current bottleneck capability** to the highest-priority non-`done` capability (prefer `in_progress`; otherwise the blocking `planned` item with the most dependency surface).
3. Add or update dated maturity promotion entries in `docs/system_contract_map.md` changelog, including rationale and milestone context.
4. Attach concrete next-step validation commands so planning remains execution-focused.

### Review command pack (next-step execution anchors)

Use generated command packs from `docs/dod_manifest.json` to avoid list drift:

- PR template-ready checklist block (all capabilities + evidence URL placeholders):
  - `python .github/scripts/render_transition_evidence.py --emit-pr-template-autogen`
- Transition-only PR evidence block for the current branch diff:
  - `python .github/scripts/render_transition_evidence.py --base <base_sha> --head <head_sha>`

Narrative planning in this document should reference those generated outputs rather than copying raw pytest command lists inline.

## Next milestone checkpoints

| Next milestone | Target date | Owner area | Pass criteria |
| --- | --- | --- | --- |
| Observer authorization contract activation | 2026-03-22 | Engine + Invariants | `tests/test_observer_frame.py` is green with authorization-scope enforcement in default mission-loop paths. |
| Capability governance contract baseline | 2026-03-29 | Engine + Contracts | Governance tests pass with policy-aware capability invocation and no regression in prediction/halt/replay contracts. |
| Repair-aware projection evolution baseline | 2026-04-05 | Engine + Contracts + Invariants | Repair-mode tests establish auditable repair-event lineage without regressing append-only replay guarantees. |
