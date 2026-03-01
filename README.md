# SemanticNG

## Refactoring focus (active)

The current project-wide focus is the refactor program defined in `src/core/REFACTORING_METAPLAN.md`.

Contributors should treat this as the active delivery objective:

- move deterministic domain logic into `src/core/`,
- keep infrastructure and I/O in adapters/shell layers,
- migrate capability-by-capability using seams, parity checks, and incremental cutovers.

### Boundary rules (repository-level)

When changing code anywhere in this repository:

- keep dependency direction pointed inward toward core logic,
- do not introduce hidden I/O into core modules,
- make contracts explicit at boundaries (inputs, outputs, errors, states),
- inject non-deterministic sources (time, ids, randomness) through ports,
- prefer slice migrations over broad rewrites.

### Contributor quick-start for refactor work

1. Pick one capability slice with clear inputs/outputs.
2. Define or tighten seam contracts first.
3. Add/route via a facade entrypoint.
4. Add parity and invariant tests for the slice.
5. Implement deterministic core logic in `src/core/`.
6. Switch routing to core once parity passes, then retire legacy path.

## Document status legend

- **Canonical**: normative for contributors.
- **Operational**: how to run/test.
- **Exploratory**: ideas/drafts.

### Document lifecycle

Exploratory → Opportunity → Roadmap → Canonical

- **Exploratory**: raw ideas.
- **Opportunity**: validated potential.
- **Roadmap**: planned work.
- **Canonical**: normative truth.

## Mission

SemanticNG is a Python project focused on state renormalization, schema selection, and behavior-driven test scenarios. See `MISSION.md` for mission, north-star principles, and phase non-goals.

Architecture and planning constraints are codified in `docs/AXIOMS.md` (normative axiom set and PR usage requirements).

Guardrail classification guidance for contributors (invariants vs policies vs heuristics) is documented in `docs/guardrails_and_invariants.md`.

## Requirements

- Python **3.10+**
- `pip` (latest recommended)

## Installation (runtime)

Install the project and its core runtime dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install .
```

## Installation for editing / development

For local development, install in editable mode with test dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

If you also want the BDD / Gherkin tooling used by the `features/` step definitions:

```bash
python -m pip install -e ".[test,bdd]"
```

## Definition-of-done manifest

A machine-readable status inventory lives at `docs/dod_manifest.json` with capability IDs, status (`done`/`in_progress`/`planned`), code paths, and test commands.
No-regression budget governance is defined in `docs/no_regression_budget.json`, including done-capability coverage, waiver schema, and expiry semantics used by CI validation.

Canonical completion criteria across capability/integration/system layers are defined in `docs/definition_of_complete.md`.

Validate this inventory in tests:

```bash
pytest tests/test_dod_manifest.py
```

### Contributor milestone policy for `src/state_renormalization/` PRs

`docs/dod_manifest.json` is the source of truth for capability status, ownership paths, and milestone pytest commands.

When your PR touches `src/state_renormalization/` or changes capability status in `docs/dod_manifest.json`, CI selects and runs the manifest-listed `pytest_commands` for relevant capabilities automatically.

### Merge expectations for milestone and maturity updates

PRs that change capability status in `docs/dod_manifest.json` or contract maturity in `docs/system_contract_map.md` are merge-ready only when all of the following are true:

- `State Renormalization Milestone Gate` is green in CI.
- `docs/dod_manifest.json` remains internally consistent and is the canonical source for capability details.
- `State Renormalization Milestone Gate` runs the manifest-selected pytest commands for the branch diff.

CI enforces these milestone rules for PRs and merge queues that touch `src/state_renormalization/`, `docs/dod_manifest.json`, or the milestone gate workflow. Other docs can be generated from the manifest as needed.


### Promotion workflow checklist

When promoting a capability status (for example `planned` -> `in_progress` or `in_progress` -> `done`), complete this checklist in the same PR:

- [ ] Update `docs/dod_manifest.json` status + capability metadata.
- [ ] Update the `ROADMAP.md` **Capability status alignment** section to mirror the transition.
- [ ] Update `docs/sprint_plan_5x.md` sprint status/exit-criteria notes so capability transition state is synchronized.
- [ ] Update `docs/system_contract_map.md` relevant contract milestone/maturity rows and add/update the changelog entry if maturity changed.
- [ ] Regenerate PR template autogen content (`python .github/scripts/render_transition_evidence.py --regenerate-pr-template`).
- [ ] Paste a transition evidence block with real CI URLs (no placeholders), including command/evidence pairs for transitioned capabilities.
- [ ] Include a PR dependency impact statement (upstream dependencies, downstream unlocks, and cross-capability regression risk).
- [ ] Declare no-regression budget impact for all affected `done` capabilities; if waived, include owner and rollback-by date.
- [ ] For governance/maturity PRs, follow the documentation freshness metadata requirement in [`docs/release_checklist.md`](docs/release_checklist.md#documentation-freshness-metadata-contributor-requirement) and update sprint handoff artifacts.

### Local one-step promotion checks

Run all promotion governance checks before pushing:

```bash
make promotion-checks
```

This command validates milestone-doc transition sync and enforces PR-template generated-content cleanliness.

### Pre-submit milestone docs check (local)

Before pushing a PR that changes milestone docs or status transitions, run:

```bash
python .github/scripts/validate_milestone_docs.py
```

Optional: set explicit environment variables to emulate CI PR context:

```bash
export BASE_SHA=<base_commit_sha>
export HEAD_SHA=<head_commit_sha>
export GITHUB_EVENT_NAME=pull_request
export GITHUB_EVENT_PATH=<path_to_pull_request_event_payload_json>
python .github/scripts/validate_milestone_docs.py
```

### pre-commit guardrails (recommended)

Install pre-commit and activate hooks locally:

```bash
python -m pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
```

Run all guardrails on demand:

```bash
pre-commit run --all-files
```

The repository hook set is defined in `.pre-commit-config.yaml` and includes:

- hygiene checks (`pre-commit-hooks`)
- `ruff` lint + format
- `mypy` type checks (configured from `pyproject.toml`)
- a fast `pytest` smoke hook on `pre-push`

## Running tests

### pytest

`pytest` is the primary test runner for all unit/integration checks under `tests/`.
Configuration is centralized in `pyproject.toml` under `[tool.pytest.ini_options]`
(`testpaths`, `pythonpath`, strict flags, and shared defaults).

Run the full pytest suite:

```bash
pytest
```

### coverage (`pytest-cov` + coverage.py)

Coverage reporting is executed through `pytest-cov`, while coverage behavior
(branch mode, source scope, omissions, and thresholds) is configured in
`pyproject.toml` under `[tool.coverage.run]` and `[tool.coverage.report]`.

Run tests with coverage:

```bash
make test-cov
# or directly:
pytest --cov --cov-report=term-missing --cov-report=xml
```

Coverage threshold governance policy (cadence, evidence requirements, waiver format,
and threshold change log) is documented in
[`docs/release_checklist.md`](docs/release_checklist.md#coverage-threshold-governance-policy).

### Coverage XML governance and review ownership

Coverage XML governance details are defined only in the release checklist policy section:
[`docs/release_checklist.md#coverage-threshold-governance-policy`](docs/release_checklist.md#coverage-threshold-governance-policy).

### mypy (optional)

`mypy` performs static type checking for `src/` and `tests/`.

```bash
mypy src tests
```

### ruff (optional)

`ruff` runs lint checks for style and common correctness issues.

```bash
ruff check src tests
```

## Current workflow (supersedes temporary integration freeze procedures)

Active contributor workflow expectations are canonical in `docs/release_checklist.md`.

- Use normal PR flow with branch protection and required CI checks enabled.
- Rebase/merge sequencing controls from `docs/integration_notes.md` are historical and non-normative unless explicitly reactivated via the objective criteria documented there.
- For milestone/maturity transitions, follow the checklist and evidence requirements in `docs/release_checklist.md`.
- If policy text conflicts, `docs/release_checklist.md` wins.

## Notes on dependencies

- `pyproject.toml` is the source of truth for package metadata and dependencies.
- `requirements.txt` is kept minimal and intended for development/test installation in this repository.
