# 5S Doctrine for Software, Systems, and Projects

**Version:** 1.2  
**Status:** Canonical  
**Applies to:** All repositories, modules, pipelines, and delivery workflows

## I. Purpose

This doctrine defines how we minimize entropy in software systems using the 5S framework:

- **Sort**
- **Set in Order**
- **Shine**
- **Standardize**
- **Sustain**

Originally derived from practices at Toyota Motor Corporation, 5S is reinterpreted here as a structural entropy-minimization discipline for knowledge systems.

Our goal is not tidiness.

Our goal is:

> Coherent systems that remain understandable, enforceable, and evolvable under change.

## II. Core Premise

Software systems accumulate invisible entropy:

- Redundant abstractions
- Drift in invariants
- Implicit contracts
- Undocumented behavior
- Dead code
- Architectural erosion

5S is our continuous canonicalization operator.

## III. System Model

Each subsystem is modeled as:

```text
S = (State, Contracts, Boundaries, Invariants, Observability)
```

Entropy increases when:

- State is ambiguous
- Contracts are implicit
- Boundaries are porous
- Invariants are unenforced
- Observability is absent

5S reduces entropy through measurable enforcement.

## IV. Canonical Surfaces (Repository-Specific)

The repository currently defines the following top-level surfaces:

```text
src/
├── core/
├── features/
├── semanticng/
└── state_renormalization/
```

These are treated as **distinct architectural strata**, not interchangeable layers.

### Role Clarification

#### `src/core`

- Canonical invariant-driven substrate.
- Must be structurally hardened.
- Highest enforcement level.

#### `src/state_renormalization`

- Architectural engine and state logic.
- Close to core.
- Must obey invariant discipline.

#### `src/semanticng`

- Package surface / distribution layer.
- Public API and integration surface.
- Must not contain hidden business logic.

#### `src/features`

- Behavioral feature modules.
- May evolve faster.
- Must not introduce invariant drift into core.

### Enforcement Tiering

| Surface | Enforcement Level |
| --- | --- |
| core | Strict |
| state_renormalization | Strict |
| semanticng | Moderate |
| features | Controlled |
| experimental | Loose |

## V. The Five Principles (Updated)

### 1️⃣ SORT (Seiri)

Remove what does not serve defined capability.

#### Operational Rules

- No unused modules in:
  - `src/core`
  - `src/state_renormalization`
- `src/features` may contain evolving capability code but must not contain orphan modules.
- `src/semanticng` must not duplicate logic from `core`.
- No unreferenced dependencies.
- No TODO without issue linkage.

#### Metrics

- `unused_symbol_count_core`
- `unused_symbol_count_state_renorm`
- `unused_symbol_count_features`
- `duplicate_logic_cross_surface`
- `orphan_module_count`

Static scan default tool: Vulture.

#### Enforcement

- CI runs unused-code scan per surface.
- New unused symbols in `core` or `state_renormalization` fail CI.
- `features` allowed warning-level until stabilized.
- Baseline allowlist permitted but must shrink.

#### Architectural Constraint

- No business logic duplication across surfaces.
- Core invariants must not be redefined elsewhere.

### 2️⃣ SET IN ORDER (Seiton)

Make structural relationships explicit.

#### Dependency Direction Rules

Allowed flows:

```text
features → state_renormalization → core
semanticng → features / state_renormalization / core
```

Disallowed flows:

```text
core → features
core → semanticng
state_renormalization → features
```

Core must remain dependency-minimal.

#### Metrics

- `cross_surface_violation_count`
- `circular_dependency_count`
- `max_import_depth`
- `% explicit state transitions in state_renormalization`

#### Enforcement

- Import-layer validation in CI.
- Circular import detection blocks merge.
- Core dependency graph audited monthly.

### 3️⃣ SHINE (Seiso)

Continuously clean to expose defects.

#### Operational Rules

- Formatting enforced automatically (e.g., Ruff).
- Type errors block merge in `core` and `state_renormalization`.
- Coverage ≥ 90% in `core`.
- Deterministic execution required in canonical surfaces.
- CI generates unused-code visibility report.

#### Metrics

- `mypy_error_count_core`
- `mypy_error_count_state_renorm`
- `coverage_core`
- `flaky_test_rate`
- `unused_code_visibility_report`

#### Enforcement Thresholds

- 0 type errors in canonical layers.
- 0 flaky tests.
- 0 new unused symbols in canonical layers.

### 4️⃣ STANDARDIZE (Seiketsu)

Convert discipline into infrastructure.

#### Operational Rules

- CI gates all merges.
- Pre-commit required.
- Version + commit hash stamped in artifacts.
- Unused-code detection automated.
- Import direction validation automated.
- Replay bundles validated for canonical capabilities.

#### Metrics

- `% automated enforcement`
- `% canonical surfaces schema-validated`
- `entropy_regression_count`

#### Enforcement Model

“No new entropy” rule:

- Existing debt allowed but tracked.
- New violations fail.

### 5️⃣ SUSTAIN (Shitsuke)

Ensure integrity persists.

#### Operational Rules

- Weekly entropy artifact generated.
- Drift detection script runs in CI.
- Technical debt tracked per surface.
- Provenance attached to outputs.

#### Metrics

- `technical_debt_growth_rate`
- `mean_time_to_green_ci`
- `invariant_violation_rate`
- `drift_alert_count`

Entropy must not silently accumulate.

## VI. Unused Code Policy (Explicit)

Unused code is defined as:

- Unreferenced symbol (static scan)
- Unreachable module (import graph)
- 0% coverage file in canonical surface
- Feature not mapped to capability ID

Policy by surface:

| Surface | Unused Code Policy |
| --- | --- |
| core | Not allowed |
| state_renormalization | Not allowed |
| semanticng | Not allowed |
| features | Warning → must resolve before promotion |

## VII. Maturity Model (Surface-Aware)

| Level | Description |
| --- | --- |
| 0 | Ad hoc entropy |
| 1 | Manual cleanup |
| 2 | CI checks exist |
| 3 | CI blocks violations |
| 4 | Invariant enforcement integrated |
| 5 | Entropy trends automatically monitored per surface |

## VIII. Canonicalization Principle

Every surface must answer:

- What is its canonical representation?
- What invariants apply?
- What other surfaces may depend on it?
- How is unused surface detected?
- How is provenance attached?

If unclear → 5S incomplete.

## IX. Non-Negotiable Constraints

- No silent mutation of state.
- No invariant redefinition outside canonical surfaces.
- No core dependency on features.
- No merging red builds.
- No new unused symbols in canonical layers.

## X. Alignment with Long-Term Mission

This structure ensures:

- Core remains epistemically stable.
- State renormalization remains mathematically coherent.
- Features can evolve without destabilizing substrate.
- SemanticNG package surface remains clean.

The purpose is to support the mission of building systems that remain:

- Coherent
- Accountable
- Adaptable
- Self-defending
