# ARCHITECTURE.md

## Purpose

This repository implements an **invariant-projected epistemic execution substrate**:

- **Contracts** define what artifacts exist and what shape they must have (`contracts.py`).
- **Invariants** define which states and transitions are admissible (`invariants.py`).
- **Engine** executes only via **projection onto the invariant surface** and records an auditable lineage (`engine.py`).

The system converges by repeatedly applying the same invariant tests across many instances (contexts, episodes, scopes), shrinking the space of plausible next steps and reducing correction cost over time.

---

## Architectural Axiom

> The system must never silently assume correctness.  
> Every irreversible action must be preceded by a **recorded prediction** and pass an **invariant gate**.

---

## Core objects and modules

### `contracts.py` — Epistemic interface surface

Contracts define the canonical artifacts exchanged between modules and persisted to storage.

Typical contract families (names illustrative; prefer your actual types):

- `PredictionRecord` — what is predicted, for which scope, in which validity window, with what evaluation plan
- `EvidenceRef` / `EvidenceMap` — references to observations and their provenance
- `ProjectionState` — materialized “current” operational state derived from history
- `CorrectionEvent` — outcome resolution + correction cost/regret attribution
- `HaltRecord` / `InvariantViolation` — explainable stop artifacts
- `CapabilityInvocation` — what capability was invoked, inputs/outputs, trace refs

> Rule: if a concept cannot be expressed as a contract, it cannot be acted upon.

---

### `invariants.py` — Constraint surface (truth conditions)

Invariants are pure, deterministic checkers over contract-validated state.

They must be:

- deterministic (same input → same output)
- machine-checkable
- fail-closed (violations stop execution)
- explainable (structured violation artifacts)

Typical invariants (IDs illustrative, align to your enums):

- **P0 Prediction Availability**: no action without a current prediction for the scope
- **P1 Write-Before-Use**: predictions must be append-verified before being consumed
- **P\* Supersession Explicitness**: prediction replacement must be explicit and traceable
- **H0 Explainable Halt**: all STOPs produce structured reason + recovery hints
- **Deterministic Projection**: projection from log → current state must be deterministic

---

### `engine.py` — Projection + gating + execution

The engine orchestrates:

1. input normalization + contract validation
2. candidate generation (optional; may be external)
3. **projection onto invariant-consistent state**
4. capability execution (only when gates open)
5. persistence (append-only)
6. explainable halting
7. reconstruction/replay from history

The engine is the only place allowed to commit state transitions.

---

## The Projection Operator (formal)

Let:

- **S** be the space of all representable states (contract-valid).
- **I = { i₁, i₂, …, iₙ }** be the set of invariants.
- **V(s)** be the set of invariant violations for state `s`.
- **Log** be an append-only event stream (PredictionLog + Evidence + Halts + Corrections).
- **P(Log)** be the deterministic projection function that produces operational state from history.

### 1) Deterministic state reconstruction

The operational state at time `t` is:

```

S_t = P(Log_≤t)

```

**Requirement:** `P` is deterministic:
```

Log_a == Log_b  ⇒  P(Log_a) == P(Log_b)

```

### 2) Candidate transition + projection gate

A step proposes a candidate transition:

```

s' = T(s, u)

```

where:
- `s` is current projected state,
- `u` is new input (observation, request, capability result, etc.),
- `T` is a candidate transition generator (may be trivial).

The system does **not** commit `s'` directly.

Instead it applies the invariant gate:

- If `V(s')` is empty: commit is allowed.
- If not: halt explainably.

In simplest (strict) form:

```

Γ(s') =  { s'          if V(s') = ∅
{ HALT(V(s')) otherwise

```

So the committed state is:

```

commit( Γ(s') )

```

### 3) Projection as iterative constraint satisfaction (optional refinement)

If you later support “repair” / “projection” (instead of immediate halt), you can define a family of projection/repair operators:

- `Π_I` maps a candidate onto the nearest admissible state under some cost `d`.
- For now, you likely run in **halt-only** mode (fail-closed), but the architecture supports both.

General form:

```

Π_I(s') = argmin_{x ∈ Adm(I)} d(x, s')

```

where `Adm(I)` is the set of states satisfying all invariants.

**Important:** even repair must be auditable: repairs become explicit events, not silent mutations.

---

## Execution pipeline (end-to-end)

### High-level loop

```

Input u_t
↓
Contract-validate u_t (contracts.py)
↓
Project operational state from log: s_t = P(Log) (engine.py)
↓
Generate candidate: s' = T(s_t, u_t) (engine.py)
↓
Evaluate invariants: V = eval_all(s') (invariants.py)
↓
If V != ∅ → HALT with structured artifact (engine.py)
Else → commit append-only events to Log (engine.py)
↓
Repeat

```

### “No action without prediction” gate

For any operation classified as “irreversible” or “externally consequential”:

- The engine must check **P0** against the relevant scope:
  - “Is there at least one current prediction for this scope?”
- If not: STOP with an explainable halt record.

---

## Persistence model

### Append-only log (source of truth)

The source of truth is an append-only stream. It may physically be JSONL, a DB table, SurrealDB events, etc. The architecture assumes:

- **never rewrite history**
- **reconstruct current state by replay/projection**

Recommended event kinds (align with your schema):

- `PredictionIssued`
- `PredictionSuperseded`
- `ObservationRecorded`
- `OutcomeResolved`
- `CorrectionRecorded`
- `CapabilityInvoked`
- `InvariantHalt`

### Materialized views (projections)

Anything “current” is a derived view:

- `CurrentPredictions(scope)`
- `CurrentBeliefState`
- `ActiveMissions`
- `OpenOutcomeWindows`

These must be reconstructible from the log.

---

## Prediction lifecycle (contract + invariants)

A prediction is not “true”; it is **testable**.

Minimum fields to keep the system learnable:

- stable prediction id
- scope (what it applies to)
- validity interval / expiry policy
- evaluation plan (how outcome will be resolved)
- evidence refs (what supports issuance)
- status: issued → current → (superseded|resolved|expired)

Invariants should enforce:

- supersession must be explicit (no silent replacement)
- “current” is a projection property, not an editable field
- resolved predictions must link to outcome evidence

---

## Explainable halts (H0)

A halt is a first-class epistemic event, not a failure.

Every STOP must produce a `HaltRecord` with:

- `invariant_id` (what failed)
- `code` (machine-readable)
- `details` (human-readable)
- `evidence_refs` (what was consulted)
- `action_hints` (how to recover, if possible)

The goal: the caller can catch, display, and recover deterministically.

---

## Capability activation architecture

### Capability Registry (authorization boundary)

Capabilities are actions the system can take (ask, fetch, compute, persist, notify, etc.).

The architecture assumes a registry that:

- declares capability contracts (input/output)
- declares preconditions (invariants or predicate checks)
- records invocations in the log
- is invoked only by `engine.py` after gating

Suggested flow:

```

engine wants capability C
↓
validate contract inputs
↓
check invariant preconditions (P0/P1/…)
↓
authorize C via registry policy
↓
execute C
↓
write CapabilityInvocation + outputs to log
↓
re-project state

````

---

## Determinism requirements

Determinism is a hard requirement for convergence.

The system must be deterministic given:

- identical log
- identical inputs
- identical configuration version

This implies:

- stable IDs derived from content/position (you already do this for Gherkin)
- deterministic ordering in projection (sort keys, stable iteration)
- no time-dependent behavior without explicit time inputs

---

## Test surface (behavior is correctness)

### Executable specifications

Behavior tests are authoritative:

- Behave/Gherkin (high-level behavior)
- Pytest (contract + invariant unit tests)

Minimum behaviors to lock early:

1. **P0**: missing current prediction → deterministic halt
2. **P1**: using prediction not append-verified → deterministic halt
3. Supersession is explicit and traceable
4. Projection determinism: replay produces same `ProjectionState`
5. Halt artifacts are structured and catchable

Example feature ideas:

```gherkin
Feature: Prediction gating

  Scenario: Engine refuses action without current prediction
    Given no current prediction exists for scope "mission:alpha"
    When the engine attempts an irreversible action in scope "mission:alpha"
    Then execution halts with invariant "P0_NO_CURRENT_PREDICTION"
    And the halt record contains action_hints

Feature: Projection determinism

  Scenario: Same log yields same projection
    Given an append-only log with events E
    When I project state twice from the same log
    Then the projection states are identical
````

---

## Convergence mechanics (why repeated invariants matter)

Each invariant test is a **constraint** that eliminates invalid next steps.

By presenting many instances of the same invariant across contexts:

* you reduce degrees of freedom in future behavior
* you improve predictability
* you lower correction cost
* you create training data aligned to “what must remain true”

In practice:

* invariants generate a high-signal dataset: (state, violation → correction)
* the engine’s behavior becomes compressible: fewer special cases, stronger guarantees
* “probable next thing” becomes constrained by invariant satisfaction

---

## File-level responsibility map

Start here when modifying correctness:

* `contracts.py`
  Defines what artifacts exist and what “well-formed” means.
* `invariants.py`
  Defines what “admissible” means and how violations are represented.
* `engine.py`
  Defines when the system can act, how it projects state, how it commits events, and how it halts.

Often adjacent:

* `adapters/persistence.py`
  Append-only event storage + read/replay interfaces.
* `features/` / `tests/`
  Executable truth definitions.

---

## Current phase boundary (implementation focus, not a limit)

In the current phase, projection operates in **strict fail-closed mode**:

* candidate transitions are either fully admissible or halted
* no silent repairs
* no autonomous invariant mutation
* correctness > performance

This phase exists to harden the substrate so future capabilities can safely expand.

---

## Appendix: Terminology

* **On-shell state**: invariant-consistent, contract-valid, admissible for execution/commit.
* **Off-shell candidate**: proposed state before gating; may violate invariants.
* **Projection**: deterministic reconstruction of operational state from immutable history.
* **Correction cost**: measure of how expensive it was to restore invariants / fix wrong predictions.
* **Convergence**: reduction of invariant violations and correction cost over time via repeated cycles.

```

### Todo/check
If you want the next step to be maximally “operational”, look for opportunities to express **minimal skeleton** for:

- `ProjectionState` + `PredictionLog` adapter interface,
- an `InvariantRegistry` with typed violation artifacts,
- and an `ExecutionEngine.step()` that implements the strict projection gate exactly as described here.
- in alignment with the achievement of other purposes
