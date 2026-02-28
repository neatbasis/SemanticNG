# SemanticNG

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
- [ ] Update `docs/system_contract_map.md` relevant contract milestone/maturity rows and add/update the changelog entry if maturity changed.
- [ ] Regenerate PR template autogen content (`python .github/scripts/render_transition_evidence.py --regenerate-pr-template`).
- [ ] Paste a transition evidence block with real CI URLs (no placeholders), including command/evidence pairs for transitioned capabilities.

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

## Running tests

Run the pytest suite:

```bash
pytest
```

Run type checks (optional):

```bash
mypy src tests
```

Run lint checks (optional):

```bash
ruff check src tests
```

## Current workflow (supersedes temporary integration freeze procedures)

Active contributor workflow expectations are canonical in `docs/release_checklist.md`.

- Use normal PR flow with branch protection and required CI checks enabled.
- Rebase/merge sequencing controls from `docs/integration_notes.md` are historical and non-normative unless explicitly reactivated via the objective criteria documented there.
- For milestone/maturity transitions, follow the checklist and evidence requirements in `docs/release_checklist.md`.

## Notes on dependencies

- `pyproject.toml` is the source of truth for package metadata and dependencies.
- `requirements.txt` is kept minimal and intended for development/test installation in this repository.
