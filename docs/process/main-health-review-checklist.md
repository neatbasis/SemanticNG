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

## Program sync control loop

- [ ] Run `make status-sync-check` and attach pass/fail output to weekly health notes.
- [ ] Confirm status schema validity for `docs/status/{project,milestones,sprints,objectives}.json`.
- [ ] Confirm relational integrity across objective `depends_on`, `milestone_id`, and `sprint_id` links.
- [ ] Confirm DoD aggregate alignment between `docs/dod_manifest.json` rollups and status document states.
- [ ] Confirm every active objective ID is referenced in both `ROADMAP.md` and `docs/sprint_plan_5x.md`.
- [ ] If drift is detected, fix status + planning docs in the same PR and rerun `make status-sync-check` before merge.

