# Quality gate policy for `main`

## Canonical enforcement scope decision

**Decision: milestone-governed enforcement for promotion/governance checks; global enforcement for baseline quality checks.**

- **Global poka-yoke blockers (always required on `main`):**
  - `Quality Guardrails / no-regression-budget`
  - `Quality Guardrails / baseline-lint-type`
  - `Quality Guardrails / baseline-test-cov`
  - `Quality Guardrails / full-type-surface`
- **Milestone/policy-surface poka-yoke blockers (conditional by changed paths):**
  - `State Renormalization Milestone Gate / baseline-quality`
  - `State Renormalization Milestone Gate / milestone-governance`
  - `promotion-governance-pokayoke` pre-commit hook (`.github/scripts/run_promotion_checks.sh`), which only runs when staged files touch milestone/policy surfaces.
- **Measurement-only telemetry (non-blocking):**
  - `Quality Guardrails / policy-measurement`
  - `State Renormalization Milestone Gate` promotion checklist measurement note emitted from `make promotion-check` step.

This repository does **not** use global blocking enforcement for promotion-governance checks outside milestone/policy surfaces.

## Required checks (branch protection baseline)

The `main` branch protection and merge queue ruleset must require, at minimum, the following always-on checks:

- `Quality Guardrails / no-regression-budget`
- `Quality Guardrails / baseline-lint-type`
- `Quality Guardrails / baseline-test-cov`
- `Quality Guardrails / full-type-surface`

In particular, `baseline-lint-type` and `full-type-surface` are mandatory required checks and must not be optional on `main`.

Milestone-gate checks remain required for PR/merge-queue entries that touch milestone-governed paths, enforced by workflow path filters.

## Temporary exceptions (time-boxed stabilization policy)

Temporary exceptions are allowed only for emergency stabilization and must satisfy all conditions below:

1. Exception is documented in a governance issue with owner + rationale.
2. Compensating control is defined (manual reviewer sign-off, scoped freeze, or narrowed merge permissions).
3. Exception has a hard sunset date and rollback plan.
4. Exception is reviewed in the next weekly "main health" review.

### Current stabilization window

- **Window start:** 2026-03-02
- **Sunset date:** 2026-04-15 (UTC)
- **Scope:** temporary waivers may only apply to queue admission; direct branch protection required checks remain unchanged.
- **Rollback requirement:** by sunset, restore strict parity so all required checks are enforced uniformly for PR and merge queue paths.

No exception may extend past 2026-04-15 without an explicit renewal PR that updates this file and includes new risk acceptance.

## Exit criteria for "stabilized"

`main` is considered stabilized only when all of the following are true:

- At least **14 consecutive days** (2+ weeks) of green `main` for required checks.
- **0 skipped required checks** across that period.
- Required-check pass rate for the period is **>= 98%**.
- Median fix time for required-check failures is **<= 1 business day**.

If any criterion regresses, stabilization status resets and the 14-day window restarts.

## Local hook enforcement policy

To prevent "green commit / red push" loops, local hooks enforce a split policy:

- `qa-commit` (pre-commit) must run lint/type plus a deterministic pytest smoke subset.
- `qa-push` (pre-push) must rerun the same smoke subset with the broader push-stage lint/format checks.
- CI remains the final authority via `baseline-test-cov` (`make qa-test-cov`) and `full-type-surface`.

This means pytest execution is required before both commit and push for baseline smoke coverage.

## Waste metrics interpretation thresholds

`docs/status/project.json` must include a `waste_metrics` block and keep these thresholds for weekly review:

- `duplicate_logic_count`: target `0`; warning at `>= 1`.
- `unused_code_delta`: target `<= 0` (no net new unused code); warning at `> 0`.
- `stale_doc_count`: target `0`; warning at `>= 1`.
- `mypy_debt_delta`: target `<= 0` (no net new debt); warning at `> 0`.
- `flaky_test_count`: target `0`; warning at `>= 1`.

Any warning-state metric requires a follow-up issue or explicit rationale in the next main-health review notes.
