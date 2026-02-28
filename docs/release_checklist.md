# Release Checklist

Use this checklist before tagging a release.

- [ ] **Milestone gate pass links recorded:** Include links to the latest successful `State Renormalization Milestone Gate` CI run(s) for this release candidate.
- [ ] **Manifest status alignment verified:** `docs/dod_manifest.json` capability statuses match both `ROADMAP.md` milestone placement and the maturity/state reflected in `docs/system_contract_map.md`.
- [ ] **Status transition evidence captured:** For each capability status transition, record the exact milestone `pytest` command(s) from `docs/dod_manifest.json` and attach passing evidence links.

## Capability and Contract Promotion Rubric

Apply these gates whenever a PR changes capability status in `docs/dod_manifest.json` or contract maturity in `docs/system_contract_map.md`.

### `planned -> in_progress`

- **Required pytest command evidence:** Include the exact command list from the transitioning capability's `pytest_commands` array in `docs/dod_manifest.json` (no paraphrasing/re-ordering).
- **Minimum evidence type:** At least one CI URL or job URL showing all listed commands passing for the branch/PR.
- **Required doc updates:**
  - Update capability status and milestone placement in `ROADMAP.md`.
  - Ensure `docs/system_contract_map.md` reflects any impacted contract references/maturity context.
  - Add a changelog note in `docs/system_contract_map.md` using the required format: `- YYYY-MM-DD (Milestone): <contract> <from> -> <to>; rationale.` when maturity is touched.
- **Exception handling:** If any gate is waived, include a rollback/follow-up note in the PR description with owner + due date + exact recovery command list.

### `in_progress -> done`

- **Required pytest command evidence:** Include the exact command list from the transitioning capability's `pytest_commands` array in `docs/dod_manifest.json` and show the full set passing.
- **Minimum evidence type:** CI URL/job URL plus at least one retained log snippet that includes the final passing summary for each required command.
- **Required doc updates:**
  - Move/update the capability entry in `ROADMAP.md` to match completed state.
  - Confirm `docs/system_contract_map.md` contract references and maturity rows are consistent with the completed behavior.
  - Add/confirm changelog entry format in `docs/system_contract_map.md`: `- YYYY-MM-DD (Milestone): <contract> <from> -> <to>; rationale.` for each maturity promotion.
- **Exception handling:** If completion is approved with a waiver, record rollback criteria and follow-up issue/PR link in the PR description.

### `prototype -> operational`

- **Required pytest command evidence:** Include the exact milestone command list from `docs/dod_manifest.json` for all capabilities referencing the promoted contract in `contract_map_refs`.
- **Minimum evidence type:** CI URL/job URL proving default runtime path tests pass for each required command.
- **Required doc updates:**
  - Update `docs/system_contract_map.md` maturity from `prototype` to `operational`.
  - Reconcile any milestone placement text in `ROADMAP.md` if promotion changes planning assumptions.
  - Add changelog entry in `docs/system_contract_map.md` with: `- YYYY-MM-DD (Milestone): <contract> <from> -> <to>; rationale.`
- **Exception handling:** If operational promotion proceeds with partial coverage, include rollback trigger and follow-up test hardening plan in the PR description.

### `operational -> proven`

- **Required pytest command evidence:** Include the exact milestone command list from `docs/dod_manifest.json` for every capability mapped to the promoted contract, including replay/halt/audit coverage where applicable.
- **Minimum evidence type:** CI URL/job URL for the passing suite and a log snippet demonstrating repeated or regression coverage in the same milestone cycle.
- **Required doc updates:**
  - Update `docs/system_contract_map.md` maturity from `operational` to `proven`.
  - Align milestone narrative in `ROADMAP.md` to reflect proven-level readiness.
  - Append changelog entry in `docs/system_contract_map.md` using: `- YYYY-MM-DD (Milestone): <contract> <from> -> <to>; rationale.`
- **Exception handling:** If `proven` is granted conditionally, include explicit rollback condition and dated follow-up verification milestone in the PR description.
