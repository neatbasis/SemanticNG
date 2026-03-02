# Weekly `main` health review checklist

Run this review weekly (recommended: Monday) and link the result in release/governance notes.

## Required-check reliability

- [ ] Collect required-check outcomes for `main` over the trailing 7 days.
- [ ] Record required-check pass rate (%).
- [ ] Confirm pass rate meets the active target in `docs/process/quality-gate-policy.md`.
- [ ] List top failing required checks and current owners.

## Median fix-time tracking

- [ ] Measure median time from first failed required-check run to first green rerun.
- [ ] Compare median fix time to the policy target.
- [ ] Identify outlier incidents and root-cause category (flake, infra, code defect, config drift).

## Required-check drift controls

- [ ] Confirm `Required Check Regression Sentinel` workflow is green.
- [ ] Confirm `Branch Protection Audit` workflow is green.
- [ ] Verify no required checks were removed/renamed without corresponding branch-protection updates.

## Stabilization status

- [ ] Confirm whether 14-day stabilization window is currently intact.
- [ ] Confirm there were no skipped required checks during the tracking period.
- [ ] If unstable, publish remediation actions with owners and due dates.
