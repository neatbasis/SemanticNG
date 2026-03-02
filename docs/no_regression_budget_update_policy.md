# No-regression budget baseline update policy

## Purpose

`docs/no_regression_budget.json` is a governance-controlled file. Baseline updates are allowed only when they keep the project fail-closed by default and include auditable change metadata.

## When baseline updates are permitted

You may update `quality_metric_budget.baseline` values only when at least one condition applies:

1. Major interpreter/runtime upgrade (for example a Python minor/major baseline move).
2. Toolchain upgrade that materially changes diagnostics (for example major Ruff/Mypy behavior changes).
3. Intentional test-surface expansion where temporary baseline noise is expected and documented.
4. Proven false-positive reclassification where command outputs changed format/semantics.

Routine drift without one of the conditions above is not permitted.

## Required artifacts for every baseline update

When `quality_metric_budget.baseline` or `quality_metric_budget.allowed_regression` changes, the PR must include:

1. Updated `docs/no_regression_budget_update_request.json` metadata.
2. PR checklist entries with:
   - before/after counts for each metric,
   - explicit justification,
   - remediation issue/PR link when counts increased.

CI enforces the metadata requirement and will fail if baseline numbers change without it.

## Allowed regression policy

- Default policy is strict: all `allowed_regression` values remain `0`.
- Re-baselining must keep `allowed_regression` at `0` unless an exception is both:
  - explicitly time-boxed (`approval_expires_on`), and
  - approved (`approved_by`) with a linked remediation plan.
- Time-boxed exceptions are temporary and must be rolled back to `0` by the expiry date.
