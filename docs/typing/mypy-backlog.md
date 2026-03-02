# Mypy Backlog Triage

_Last updated: 2026-03-02_

## Scope snapshots

### baseline-lint-type (Tier 1)
Command:

```bash
mypy --config-file=pyproject.toml src/state_renormalization src/core
```

Result:

```text
Success: no issues found in 14 source files
```

### full-type-surface (Tier 2)
Command:

```bash
mypy --config-file=pyproject.toml src tests
```

Result: **42 errors in 14 files** (all in tests).

## Prioritization policy

Priority order for fixes:

1. **P0 — Config/import errors and missing stubs** (blockers)
2. **P1 — `Any` leaks at package boundaries**
3. **P2 — Internal strictness issues** (e.g., `no-untyped-def`, indexing/narrowing in tests)

Current status:

- **P0**: none detected in current Tier 1/Tier 2 runs (no third-party import/stub errors).
- **P1**: baseline package-boundary leaks in `src/state_renormalization` resolved for current Tier 1 scope.
- **P2**: remaining debt is test-surface strictness work.

## Third-party import/stub handling

No third-party `Cannot find implementation or library stub` errors were observed in the captured runs, so no new stub package pins or mypy import overrides were added in this update.

If import errors appear in future runs, handle in this order:

1. Add/pin the corresponding `types-*` package in `pyproject.toml` (preferred).
2. If no maintained stubs exist, add a **targeted** `[[tool.mypy.overrides]]` for the specific module path with an inline TODO + owner + removal sprint.

## Backlog grouped by module path

| Module path | Error count | Error classes | Priority bucket | Owner tag |
|---|---:|---|---|---|
| `tests/test_observer_frame.py` | 12 | `no-untyped-def` (11), `union-attr` (1) | P2 | `@team-governance-runtime` |
| `tests/test_render_transition_evidence.py` | 6 | `no-untyped-def` (6) | P2 | `@team-devex-tooling` |
| `tests/test_repair_events_auditability.py` | 6 | `no-untyped-def` (2), `index` (2), `call-overload` (1), `attr-defined` (1) | P2 | `@team-repair-lineage` |
| `tests/test_capability_invocation_governance.py` | 4 | `no-untyped-def` (4) | P2 | `@team-governance-runtime` |
| `tests/test_engine_projection_mission_loop.py` | 2 | `no-untyped-def` (2) | P2 | `@team-governance-runtime` |
| `tests/test_predictions_contracts_and_gates.py` | 2 | `no-untyped-def` (1), `index` (1) | P2 | `@team-contracts` |
| `tests/test_repair_acceptance_policy.py` | 2 | `no-untyped-def` (2) | P2 | `@team-repair-lineage` |
| `tests/test_replay_projection_analytics.py` | 2 | `no-untyped-def` (1), `arg-type` (1) | P2 | `@team-replay-analytics` |
| `tests/replay_projection_analytics/test_append_only_replay.py` | 1 | `no-untyped-def` (1) | P2 | `@team-replay-analytics` |
| `tests/test_doc_freshness_slo.py` | 1 | `no-untyped-def` (1) | P2 | `@team-devex-tooling` |
| `tests/test_repair_mode_projection.py` | 1 | `no-untyped-def` (1) | P2 | `@team-repair-lineage` |
| `tests/test_repair_mode_projection_multiturn.py` | 1 | `no-untyped-def` (1) | P2 | `@team-repair-lineage` |
| `tests/test_replay_projection_determinism.py` | 1 | `no-untyped-def` (1) | P2 | `@team-replay-analytics` |
| `tests/test_replay_projection_restart_contracts.py` | 1 | `no-untyped-def` (1) | P2 | `@team-replay-analytics` |

## Sprint error budget target

- **Global target**: reduce **6 mypy errors/week** in Tier 2 until backlog reaches 0.
- **Per-sprint target (2 weeks)**: reduce **12 errors/sprint**.
- **Guardrail**: no regressions allowed in Tier 1 (`baseline-lint-type` must remain at 0).

### Suggested sprint sequence

1. **Sprint N**: clear `tests/test_observer_frame.py` and `tests/test_render_transition_evidence.py` (18 errors).
2. **Sprint N+1**: clear repair-lineage modules (10 errors).
3. **Sprint N+2**: clear replay + contracts remainder (14 errors).
