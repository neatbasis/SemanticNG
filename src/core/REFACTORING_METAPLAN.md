Here is a repo-ready document you can drop in as `REFACTORING_METAPLAN.md`.

---

# REFACTORING_METAPLAN.md

## Purpose

This metaplan defines how the codebase is refactored into a state where the **core functionality is implemented cleanly in `src/core/`**, with clear boundaries, deterministic behavior, and long-term maintainability.

This is not a one-time task. It is a repeatable, invariant-driven process applied incrementally.

---

# North-star objective

The primary objective of this refactor phase is:

> Establish `src/core/` as the single authoritative location for domain logic that is deterministic, composable, and independent of infrastructure.

Success means:

* Core logic can be executed and tested without infrastructure.
* Core logic is governed by explicit contracts and invariants.
* Infrastructure integrates with core via clearly defined ports.
* Legacy code becomes replaceable and removable.

---

# Core boundary rules (non-negotiable)

These rules define what is allowed inside `src/core`.

## Core MUST

* Define domain logic.
* Define contracts (data structures, states, outcomes).
* Define ports (interfaces describing external needs).
* Be deterministic given explicit inputs.
* Be testable without infrastructure setup.

## Core MUST NOT

* Perform I/O (filesystem, network, database, device access).
* Depend on frameworks, adapters, or infrastructure code.
* Depend on environment state implicitly.
* Depend on global mutable state.
* Import from legacy or adapter modules.

---

# Architectural principles

These principles guide all refactoring decisions.

## 1. Dependency inversion

Core defines needs. Infrastructure satisfies them.

Dependencies must point inward toward core.

Never the reverse.

---

## 2. Functional core, imperative shell

Core:

* Pure logic
* Explicit state transitions
* Deterministic behavior

Shell (adapters):

* I/O
* Integration
* Execution coordination

---

## 3. Contract-first development

All boundaries are defined by explicit contracts.

Contracts define:

* Inputs
* Outputs
* Errors
* States

Implementations fulfill contracts.

Contracts remain stable even as implementations evolve.

---

## 4. Strangler-fig refactoring

Legacy behavior is replaced incrementally, not rewritten wholesale.

Each capability is migrated slice-by-slice behind stable seams.

Legacy is removed only after parity and adoption are confirmed.

---

## 5. Determinism and explicit state

Core must not depend on implicit sources of nondeterminism.

All variability must be injected through ports.

Examples include:

* Time
* ID generation
* Randomness
* Persistence

---

## 6. Invariant-driven correctness

Core correctness is defined by invariants, not incidental behavior.

Invariants describe what must always be true.

Tests enforce invariants continuously.

---

# Refactoring loop (apply per capability slice)

Each capability is migrated using this repeatable cycle.

## Step 1: Identify slice

Choose one capability with:

* Clear inputs
* Clear outputs
* Clear purpose

Avoid large, ambiguous migrations.

---

## Step 2: Define seam contracts

Define explicit contracts describing:

* Inputs
* Outputs
* State transitions
* Error outcomes

These become stable boundaries.

---

## Step 3: Introduce facade

Create a facade that becomes the single entry point.

Facade routes execution to:

* legacy implementation, or
* core implementation

Routing must be controllable and observable.

---

## Step 4: Establish parity tests

Create golden/parity tests that:

* Capture representative inputs
* Compare legacy and core outputs
* Normalize nondeterministic values

Parity ensures behavior preservation.

---

## Step 5: Implement core logic

Implement logic in `src/core/` following boundary rules.

Core must:

* Depend only on contracts and ports
* Be deterministic
* Be composable

---

## Step 6: Switch routing to core

Once parity and invariant tests pass, route execution to core.

Legacy remains available temporarily for rollback safety.

---

## Step 7: Remove legacy

Once legacy is unused and parity confirmed:

* Remove legacy implementation
* Remove routing logic
* Simplify architecture

This completes the slice migration.

---

# PR checklist (required for all refactoring PRs)

Every refactoring PR must satisfy:

## Boundary integrity

* [ ] Core does not import adapters or legacy
* [ ] Core contains no I/O
* [ ] Dependencies point inward toward core

## Contract clarity

* [ ] Contracts are explicit
* [ ] Inputs and outputs are well-defined
* [ ] Error states are explicit

## Determinism

* [ ] No implicit time access
* [ ] No implicit ID generation
* [ ] No implicit randomness

## Test coverage

* [ ] Parity tests exist (if replacing legacy)
* [ ] Invariant tests exist
* [ ] Tests run without infrastructure setup

## Simplicity

* [ ] Logic is understandable locally
* [ ] Responsibilities are clearly separated

---

# Migration ledger template

Track slice migrations using this table:

| Slice              | Facade | Core Implemented | Parity Tests | Legacy Routed | Legacy Removed |
| ------------------ | ------ | ---------------- | ------------ | ------------- | -------------- |
| Example capability | yes    | yes              | yes          | yes           | no             |

This ledger prevents ambiguity about migration progress.

---

# Definition of done for refactor phase

Refactor phase is complete when:

* All domain logic resides in `src/core`
* Infrastructure exists only in adapters
* Contracts govern all boundaries
* Core is deterministic and independently testable
* Legacy logic has been removed or isolated

---

# Anti-goals (explicitly out of scope)

These activities are not objectives of this phase:

* Large-scale rewrites without seams
* Simultaneous migration of unrelated capabilities
* Introducing new infrastructure abstractions prematurely
* Optimizing before clarity is achieved
* Collapsing core and adapter responsibilities

Clarity and correctness take precedence over speed.

---

# Guiding principle

The goal is not merely to reorganize code.

The goal is to establish a system where:

* logic is explainable,
* behavior is predictable,
* and correctness is enforceable.

Every refactoring step should move the system toward that state.

---
 `README.md` that enforces the boundary rules locally so contributors immediately understand the current focus and how to work inside the SemanticNG project
 `src/core/README.md` that enforces the boundary rules locally so contributors immediately understand how to work inside core.
 `src/semanticng/README.md` that enforces the boundary rules locally so contributors immediately understand how to work inside semanticng.
 `src/state_renormalization/README.md` that enforces the boundary rules locally so contributors immediately understand how to work inside state_renormalization

IMPLEMENTATION STATUS: Not implemented. As the project is now, a fresh contributor and a user will not know what the next steps forward with this project are.
TODO: Proggres toward a clean state as defined by the boundary conditions

_Last regenerated from manifest: 2026-03-01T16:17:40Z (UTC)._
