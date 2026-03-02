# CORE_ISOLATION_PROTOCOL

This protocol operationalizes `src/core` constraints into change policy, evidence requirements, and release-blocking classes.

## Normative mappings

### Invariant mapping (`src/core/INVARIANTS.md`)
- **I1 Surface minimality** (`Exports(M_core) = {__version__}`) governs API/export edits.
- **I2 Version provenance** (`__version__` imported from `semanticng._version`) governs provenance edits.
- **I3 No orchestration** (no feature/workflow semantics in `src/core`) governs layering edits.

### Capability mapping (`src/core/CAPABILITY_LEVELS.md`)
- **L0**: protocol is documented and linked from core governance docs.
- **L1**: export/provenance surface is testable and machine-checkable.
- **L2**: change classes include required evidence before merge.
- **L3**: violation classes are release-blocking and CI-visible.

### CI/hook control mapping
- **Pre-commit / local gate**: `.pre-commit-config.yaml` hook `qa-commit-stage` runs `scripts/ci/run_stage_checks.py qa-commit`, which includes `python scripts/ci/check_core_isolation_protocol.py` for core-path changes.
- **Pre-push / local gate**: `.pre-commit-config.yaml` hook `qa-push-stage` runs `scripts/ci/run_stage_checks.py qa-push`, including the same protocol check.
- **CI baseline gate**: `.github/workflows/quality-guardrails.yml` job `baseline-lint-type` runs canonical baseline checks (`make qa-baseline`) that execute these hooks.
- **Milestone gate**: `.github/workflows/state-renorm-milestone-gate.yml` enforces parity targets (`make qa-hook-parity`) and therefore inherits protocol hook execution.

## Allowed changes

1. **Documentation-only clarification** in `src/core/*.md` that does not alter invariants/capability intent.
2. **Version plumbing maintenance** preserving:
   - `from semanticng._version import __version__`
   - `__all__ = ["__version__"]`
3. **Non-semantic hygiene** (formatting/comments/types) in `src/core/*.py` with no API expansion and no orchestration semantics.
4. **Constraint-tightening checks** that strengthen detectability of I1/I2/I3 violations.

## Prohibited changes

1. **Public surface growth** (any new export from `src/core/__init__.py`) — violates I1.
2. **Version provenance drift** (deriving `__version__` from any source other than `semanticng._version`) — violates I2.
3. **Orchestration leakage** into `src/core` (feature flow, scenario/step logic, workflow/pipeline semantics) — violates I3.
4. **Cross-layer imports** from orchestration/application namespaces into `src/core` (for example `state_renormalization`, `features`) — I3 breach indicator.

## Required evidence by change type

- **E1: Export/provenance edits (I1/I2-sensitive)**
  - Updated diff showing `src/core/__init__.py` keeps one-symbol export.
  - Passing policy check output from `python scripts/ci/check_core_isolation_protocol.py`.
  - Passing invariant/contract tests from stage checks.

- **E2: Core Python logic edits (I3-sensitive)**
  - Passing policy check output with no forbidden imports/orchestration markers.
  - Brief reviewer note naming affected invariant(s) and why no layering leakage exists.
  - Stage check pass (`qa-commit`/`qa-push`) attached to PR evidence.

- **E3: Core governance doc edits**
  - Mapping parity maintained across `INVARIANTS.md`, `CAPABILITY_LEVELS.md`, and this protocol.
  - No contradiction with CI/hook control mapping.

## Release-blocking violation classes

- **RB-1 Contract break (hard block)**
  - Any I1 or I2 violation (extra exports, missing `__all__`, wrong version source).
- **RB-2 Layering breach (hard block)**
  - Any I3 violation (orchestration semantics or cross-layer orchestration imports in `src/core`).
- **RB-3 Evidence failure (hard block)**
  - Required evidence for E1/E2/E3 is missing or contradictory.
- **RB-4 Control drift (hard block)**
  - Protocol mapping diverges from `.pre-commit-config.yaml` hooks or relevant workflow jobs.

## Automation scope and limits

`scripts/ci/check_core_isolation_protocol.py` intentionally detects **obvious** breaches in staged `src/core` diffs:
- extra exports,
- forbidden imports,
- orchestration leakage markers.

It is a guardrail, not a semantic proof; reviewer judgment and invariant tests remain normative for ambiguous cases.
