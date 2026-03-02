# Quality gate policy for `main`

## Required checks (branch protection baseline)

The `main` branch protection and merge queue ruleset must require, at minimum, the following checks:

- `Quality Guardrails / no-regression-budget`
- `Quality Guardrails / baseline-lint-type`
- `Quality Guardrails / baseline-test-cov`
- `Quality Guardrails / full-type-surface`
- `State Renormalization Milestone Gate / baseline-quality`
- `State Renormalization Milestone Gate / milestone-governance`

In particular, `baseline-lint-type` and `full-type-surface` are mandatory required checks and must not be optional on `main`.

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
