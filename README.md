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

Validate this inventory in tests:

```bash
pytest tests/test_dod_manifest.py
```

### Contributor milestone policy for `src/state_renormalization/` PRs

When your PR touches `src/state_renormalization/`, include milestone test evidence in the PR description (or linked CI run) for every relevant `pytest_commands` entry defined in `docs/dod_manifest.json`:

- Capabilities with `status: in_progress` whose `code_paths` overlap your changed files.
- Any capability moved from `in_progress` to `done` in the same PR.

Status transitions from `in_progress` to `done` must include all of the following:

1. Passing evidence for that capability's manifest-listed `pytest_commands`.
2. Documentation updates in `README.md` and/or `docs/*.md` beyond `docs/dod_manifest.json`.
3. PR checklist links to CI evidence for each listed command (workflow/job URL or attached command output).

### Merge expectations for milestone and maturity updates

PRs that change capability status in `docs/dod_manifest.json` or contract maturity in `docs/system_contract_map.md` are merge-ready only when all of the following are true:

- `State Renormalization Milestone Gate` is green in CI.
- The PR body includes exact manifest command strings plus passing evidence links for each command.
- `ROADMAP.md` and `docs/system_contract_map.md` are updated for status transitions.
- Contract maturity promotions include a dated changelog entry under `docs/system_contract_map.md`.

CI enforces these milestone rules for PRs and merge queues that touch `src/state_renormalization/`, `docs/dod_manifest.json`, or the milestone gate workflow.

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

## Notes on dependencies

- `pyproject.toml` is the source of truth for package metadata and dependencies.
- `requirements.txt` is kept minimal and intended for development/test installation in this repository.
