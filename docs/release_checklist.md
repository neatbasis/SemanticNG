# Release Checklist

Use this checklist before tagging a release.

## Canonical contributor workflow expectations

This document is the canonical source for active release/integration workflow expectations.

DMAIC change-type routing (required files, validators, evidence locations, and merge-blocking criteria) is defined in [`docs/documentation_change_control.md`](documentation_change_control.md).

- Default to standard PR flow with branch protection and required checks enabled.
- Use milestone gate + manifest evidence as merge prerequisites for milestone/maturity changes.
- Treat `docs/integration_notes.md` as historical context only unless its explicit activation criteria are met.

- [ ] **Milestone gate pass requirement:** Include link(s) to the latest successful `State Renormalization Milestone Gate` CI run(s) for this release candidate.
- [ ] **Manifest evidence mapping requirement:** `docs/dod_manifest.json` remains canonical, and each transitioned capability has complete `pytest_commands` entries synchronized with `ci_evidence_links.command` in manifest order.
- [ ] **Optional evidence duplication guidance:** Duplicate gate-pass links in PR body and/or release notes only when extra visibility is useful; manifest evidence remains the source of truth.


## Governance enforcement requirements

- [ ] **No-regression budget respected:** All `done` capability command packs remain green with zero unapproved failures.
- [ ] **No-regression policy source stays canonical:** `docs/no_regression_budget.json` remains synchronized with done capability IDs, waiver records, and expiry semantics.
- [ ] **Regression waiver timeboxed:** Any waiver includes owner, rationale, rollback-by date, and mitigation command packs.
- [ ] **Dependency impact statements present:** Every merged PR includes upstream/downstream impact and cross-capability risk statements.
- [ ] **Capability maturity gates enforced:** `planned -> in_progress -> done` transitions are validated by CI entry/exit gate checks.
- [ ] **Documentation freshness SLO met:** `docs/doc_freshness_slo.json` governs the freshness metadata policy and `python .github/scripts/validate_doc_freshness_slo.py --config docs/doc_freshness_slo.json` passes.
- [ ] **Sprint handoff minimum artifacts attached:** Sprint-close report includes exit table, open-risk register, and next-sprint preload list.

### Documentation freshness metadata (contributor requirement)

For every Markdown file governed by `docs/doc_freshness_slo.json`, include this exact metadata line near the end of the file and refresh it whenever governance-significant content changes:

`_Last regenerated from manifest: YYYY-MM-DDTHH:MM:SSZ (UTC)._`

Use UTC only, keep the trailing `Z`, and do not alter punctuation/format. The validator enforces this pattern and freshness age SLO:

```bash
python .github/scripts/validate_doc_freshness_slo.py --config docs/doc_freshness_slo.json
```

## `pyproject.toml` quality-tooling change controls

Apply this section whenever a PR modifies `pyproject.toml` entries that affect `pytest`, `mypy`, or `coverage` behavior.

### Required reviewers/owners

- [ ] **Code owner review:** At least one maintainer with ownership of CI/governance workflows (`.github/workflows/*`) approves the PR.
- [ ] **Quality gate owner review:** At least one reviewer accountable for test/static-analysis policy confirms the new settings and rationale.
- [ ] **Release/governance acknowledgement for threshold/policy shifts:** Required when changing blocking semantics (for example: coverage fail-under, strictness toggles, warning-as-error behavior).

### Required before/after command evidence

Attach before/after evidence in the PR description or linked artifact for each affected gate:

- [ ] `pytest --cov --cov-report=term-missing --cov-report=xml`
- [ ] `mypy .`
- [ ] Any additional command newly required by the `pyproject.toml` change.

Evidence expectations:

1. Provide both a **before** run (baseline branch or pre-change commit) and an **after** run (PR head).
2. Include exit status and key summary lines (test counts, mypy error totals, coverage percent/fail-under check).
3. Link to the exact CI run URL or uploaded artifact for reproducibility.

### CI workflow compatibility checks

Before merge, confirm `.github/workflows/quality-guardrails.yml` remains aligned with updated `pyproject.toml` gates:

- [ ] Every changed `pyproject` quality section maps to at least one CI command in `Quality Guardrails`.
- [ ] Command flags in CI are still compatible with updated defaults/strictness from `pyproject.toml`.
- [ ] If a new section/tool is introduced, add or update a CI workflow step in the same PR.
- [ ] PR notes include the mapping update reference (see table in `.github/workflows/quality-guardrails.yml`).

## Coverage threshold governance policy

This section is the canonical policy for coverage threshold governance.

### Coverage XML artifact generation, location, and review accountability

- `coverage.xml` is generated by `make test-cov` or `pytest --cov --cov-report=term-missing --cov-report=xml`.
- CI expectation: `coverage.xml` must exist at the repository root for the coverage run and be attached/published as an artifact referenced from PR or sprint-close evidence.
- Review ownership:
  - PR stage: PR author + assigned reviewer verify artifact presence and percent summaries.
  - Sprint-close/release stage: release/governance owner verifies artifact linkage in handoff/release evidence.

### Coverage failure triage (blocking vs. advisory)

- **Blocking failures** (must be resolved or waived before merge/close):
  - `coverage.xml` missing from required CI coverage context.
  - Coverage check fails configured threshold in `pyproject.toml` (`[tool.coverage.report].fail_under`).
  - Negative threshold delta is introduced without approved cadence exception/waiver.
- **Advisory findings** (document and monitor, do not block by default):
  - Changed-module coverage declines while global threshold remains passing.
  - Coverage drift is attributable to scoped refactor churn and is paired with a recovery note/target sprint in handoff artifacts.

### Threshold source of truth

- Coverage threshold authority is `pyproject.toml` under `[tool.coverage.report].fail_under`.
- Current configured threshold: **85**.
- Any PR discussion, checklist, or sprint note that references a different threshold is non-authoritative until `pyproject.toml` is updated.

### Allowed change cadence

- Threshold changes are allowed only at declared sprint boundaries (sprint planning kickoff or sprint close).
- Out-of-band changes require an explicit waiver (see waiver format below) and approval from the designated release/governance owner.

### Required evidence for threshold changes

For both threshold increases and decreases, the PR must include:

1. Link to a successful CI run showing `pytest --cov` output and resulting percentage.
2. A short rationale describing the motivating code/test delta.
3. Impact statement covering expected effect on near-term delivery risk.

Additional requirement for decreases:

4. Recovery plan with target sprint/date for restoring or exceeding the prior threshold.

### Waiver format and expiration

If cadence or evidence requirements cannot be fully met, include a timeboxed waiver using this structure:

```markdown
Coverage governance waiver:
- Owner: <name/github-handle>
- Requested on: <YYYY-MM-DD>
- Scope: <cadence exception and/or missing evidence>
- Rationale: <why waiver is needed>
- Mitigations: <temporary controls while waiver is active>
- Expires on: <YYYY-MM-DD>
- Follow-up issue/PR: <link>
```

Waivers expire automatically at the stated date and must be removed or renewed with fresh approval before further threshold changes.

### Threshold change log

Record every accepted threshold update in reverse chronological order.

| Date (UTC) | Change (`from -> to`) | Rationale | CI evidence URL |
| --- | --- | --- | --- |
| 2026-03-01 | `85 -> 85` | Baseline governance log entry added to document current enforced threshold and establish audit trail format. | https://github.com/example/semanticng/actions/runs/REPLACE_WITH_RUN_ID |

## Copy/paste evidence block (validator-compatible)

Generate the PR-template block from `docs/dod_manifest.json` instead of maintaining command examples here:

```bash
python .github/scripts/render_transition_evidence.py --emit-pr-template-autogen
```

Use the generated capability sections where needed (PR notes, release notes, or docs). URLs default to the current CI run URL when generated in GitHub Actions.

## Merge expectations for milestone and maturity PRs

Do not merge milestone or maturity update PRs until all conditions are met:

1. `State Renormalization Milestone Gate` CI is passing on the PR head SHA.
2. `docs/dod_manifest.json` contains the canonical command/evidence mapping for transitioned capabilities.
3. `python .github/scripts/validate_doc_freshness_slo.py --config docs/doc_freshness_slo.json` passes for governed docs before merge.

## Exceptional integration stabilization controls (reactivation only)

Use these controls only when the activation criteria in `docs/integration_notes.md` are met:

- [ ] **Merge freeze scope explicitly declared:** Conflict-prone files and governance docs in scope are listed in the integration plan.
- [ ] **Stack merged serially in defined order:** Integration merges are landed one-by-one (not in parallel) with immediate follow-up rebases.
- [ ] **Post-merge validation run after each landed PR:** Conflict-prone suites and governance validation pass before moving to the next PR.
- [ ] **Superseded PRs closed with `merged-via-integration` notes:** Every superseded PR includes links to preserving integration commits and a feature-retention summary.

## Integration PR feature-retention checklist

When preparing an integration PR that reconciles multiple incoming branches, include a feature-retention section in the PR body that enumerates each still-open PR and the exact preserved behavior(s).

Use this template:

```markdown
## Feature-retention checklist

- [ ] PR #<number> — <short title>
  - Preserved behavior: <specific behavior retained after reconciliation>
  - Validation command: `<exact command>`
  - Evidence: <https://... or artifact://...>
- [ ] PR #<number> — <short title>
  - Preserved behavior: <specific behavior retained after reconciliation>
  - Validation command: `<exact command>`
  - Evidence: <https://... or artifact://...>
```

If conflict reconciliation drops or defers any behavior, do not merge immediately: open follow-up patch PR(s) in the same integration cycle and link them under the affected checklist entry.

_Last regenerated from manifest: 2026-03-01T00:00:00Z (UTC)._
