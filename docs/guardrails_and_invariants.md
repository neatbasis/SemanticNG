# Guardrails and invariants

This document defines a shared classification model for runtime decision logic in SemanticNG.

For the normative architecture/planning boundary layer above this classification model, see `docs/AXIOMS.md` (axioms constrain what may be designed; invariants/policies/heuristics classify how runtime logic is implemented).

## Why this exists

Several runtime components combine strict correctness checks, governance defaults, and ranking logic.
When these are mixed in a single branch tree, reviews and extensions become brittle.

Use this split everywhere possible:

1. **Invariants** — truth boundaries; violations are invalid/unsafe.
2. **Policies** — governance defaults; can be waived with rationale.
3. **Heuristics** — search/ranking/estimation; can be wrong without invalidating the run.

## Classification litmus

For each condition, ask:

- If false, is the system **invalid**? → invariant.
- If false, is it **non-ideal but acceptable**? → policy.
- If false, is it only **less likely / lower quality**? → heuristic.

## Invariants (must never be violated)

Treat a condition as an invariant when violating it causes one of:

- Undefined state semantics.
- Safety/trust breach.
- Broken audit/reconstructibility.
- Contract shape invalidity.

### Project guardrail examples

- Halt records must contain normalized explainability fields and pass halt payload validation (`invariant_id`, `details`, `evidence`).
- Invariant gate outcomes must deterministically resolve to `Flow.CONTINUE`/`Flow.STOP` and produce contract-compliant payloads.
- Observer authorization scope must permit gated invariant evaluation.

Reference implementations and tests:

- `src/state_renormalization/invariants.py`
- `src/state_renormalization/engine.py`
- `tests/test_predictions_contracts_and_gates.py`
- `tests/test_contracts_halt_record.py`
- `tests/test_observer_frame.py`

## Policies (defaults and governance)

Policies encode preferred behavior and escalation rules. Policies are expected to vary by mode/channel/capability and may be waived when explicit rationale exists.

### Project policy examples

- Capability invocation guard decisions (`allow` vs policy denial) with policy codes and halt metadata.
- Observation freshness routing (`continue`, `ask_request`, `hold`) from adapter-provided freshness contracts.
- Clarification preference when ambiguity-focused selector rules apply.

Reference implementations and tests:

- `src/state_renormalization/engine.py`
- `src/state_renormalization/adapters/observation_freshness.py`
- `src/state_renormalization/adapters/schema_selector.py`
- `tests/test_capability_invocation_governance.py`
- `tests/test_capability_adapter_policy_guards.py`

## Heuristics (best-effort ranking)

Heuristics propose candidates or scores under uncertainty. A bad heuristic result should degrade quality, not violate validity.

### Project heuristic examples

- Schema selector rule-matching and candidate ordering by phase and registration order.
- Ambiguity candidate suggestions and score ordering in schema-selection outputs.

Reference implementations and tests:

- `src/state_renormalization/adapters/schema_selector.py`
- `tests/test_schema_selector.py`

## Recommended implementation pattern

For features that mix uncertainty and guardrails, use explicit staged outputs:

1. `heuristics.propose(ctx) -> candidates (+ scores)`
2. `invariants.check(ctx, candidates) -> violations`
3. `policies.decide(ctx, candidates, violations) -> action + findings (+ waiver)`

Benefits:

- More stable branching and fewer ad-hoc exceptions.
- Better explainability for why an action was selected.
- Cleaner extension points for domain-specific behavior.

## Smells that indicate refactor opportunity

Refactor when you see one or more of:

- `should`/`typically` checks implemented as hard errors.
- Exceptions used for expected ambiguity.
- Hard-coded thresholds with no owner/rationale artifact.
- ask-vs-act branching mixed with schema validity checks.
- Decisions only explainable by replaying nested `if/else` code.

## Current project baseline

SemanticNG already has a strong invariant substrate in prediction/evidence/halt contracts and gate evaluation.
Recent selector work added explicit pipeline artifacts for candidate proposal, invariant validation, and policy decision.

Keep advancing toward explicit decision records where every outward action can be explained from:

- invariant violations,
- policy findings/waivers,
- heuristic candidate scores/ranks.
