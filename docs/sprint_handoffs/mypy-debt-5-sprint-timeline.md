# Mypy debt burn-down timeline (5 sprints)

This timeline sequences the suppression inventory, KPI tracking, and override-removal workstream captured in `docs/mypy_debt.md`.

## Sprint 6 — Inventory + reporting bootstrap

### Scope

- Land inventory script for parsing `pyproject.toml` `[[tool.mypy.overrides]]` suppressions.
- Publish suppression baseline table with owners, blockers, and target-removal sprints.

### Exit criteria

- `python .github/scripts/mypy_override_inventory.py --format markdown` runs in CI/local and emits current suppression inventory.
- `docs/mypy_debt.md` contains the canonical suppression table and sprint KPI baseline.
- Release checklist includes debt-delta review requirement when mypy overrides change.

## Sprint 7 — BDD suppression tranche reduction

### Scope

- Remove or narrow BDD step-glue suppressions (`disallow_*` and `warn_return_any` overrides).
- Introduce typed Behave context protocol and decorator-facing annotations for step modules in active use.

### Exit criteria

- At least 8 suppression rows removed from baseline inventory.
- No net increase in disabled mypy rules for BDD modules.
- Any remaining BDD suppressions have updated blockers and a removal date <= Sprint 8.

## Sprint 8 — Optional-dependency wrapper boundary hardening

### Scope

- Reduce `warn_return_any = false` reliance in `semanticng.bdd_compat` and `semanticng.deeponto_compat`.
- Replace dynamic runtime boundary paths with typed wrappers/stubs where feasible.

### Exit criteria

- `semanticng.bdd_compat` and/or `semanticng.deeponto_compat` suppression inventory count reduced from Sprint 7 baseline.
- Engine/adapters `Any` KPI reaches at least 40% reduction from Sprint 5 baseline.
- Disabled-rule set shrinks to `<= 6` entries.

## Sprint 9 — Test-tree strictness convergence

### Scope

- Reduce broad `tests` / `tests.*` override relaxations by tightening high-signal rules.
- Expand contract-sensitive strict typing patterns into general-behavior tests.

### Exit criteria

- Net suppression count is at least 14 rows below Sprint 5 baseline.
- Disabled-rule set shrinks to `<= 4` entries.
- Sprint handoff includes debt trend snapshot generated from inventory script and explicit open blockers.

## Sprint 10 — Release-gate readiness for minimal suppressions

### Scope

- Finalize remaining planned suppressions and codify steady-state governance thresholds.
- Enforce debt delta review as standard release checklist behavior.

### Exit criteria

- All planned-to-remove suppressions are removed (>=18-row cumulative reduction).
- Remaining override relaxations are approved as long-lived exceptions with named owners and annual review cadence.
- Release candidate evidence includes before/after suppression inventory and reviewer sign-off for any remaining debt.
