# Documentation Index

This file is the single entrypoint for repository documentation.

## Top-level taxonomy

- **Mission** — Why the project exists, what outcomes matter, and what is explicitly out of scope. **When to read this:** start here if you need product intent or decision framing before changing code.
  - [MISSION.md](../MISSION.md)
  - [docs/AXIOMS.md](AXIOMS.md)
- **Architecture** — System boundaries, contracts, and structural maps for implementation and refactors. **When to read this:** use before changing component boundaries, interfaces, or cross-module behavior.
  - [ARCHITECTURE.md](../ARCHITECTURE.md)
  - [docs/architecture-map.md](architecture-map.md)
  - [docs/system_contract_map.md](system_contract_map.md)
- **Governance** — Policies, quality gates, and change-control rules that can block merges. **When to read this:** use before opening a PR that changes capability state, contracts, or quality policy.
  - [docs/release_checklist.md](release_checklist.md)
  - [docs/documentation_change_control.md](documentation_change_control.md)
  - [docs/definition_of_complete.md](definition_of_complete.md)
  - [docs/dod_manifest.json](dod_manifest.json)
  - [docs/no_regression_budget.json](no_regression_budget.json)
- **Development** — Local setup, editor/toolchain parity, and command packs for day-to-day contribution flow. **When to read this:** use on first clone and whenever local checks differ from CI.
  - [docs/DEVELOPMENT.md](DEVELOPMENT.md)
  - [CONTRIBUTING.md](../CONTRIBUTING.md)
  - [docs/editor_setup.md](editor_setup.md)
  - [docs/dev_toolchain_parity.md](dev_toolchain_parity.md)
- **Release** — Pre-release validation and operational controls for shipping safely. **When to read this:** use before tag/release decisions or branch-protection audits.
  - [docs/release_checklist.md](release_checklist.md)
  - [docs/branch_protection_audit.md](branch_protection_audit.md)
  - [docs/process/quality-gate-policy.md](process/quality-gate-policy.md)
- **Sprint / handoffs** — Sprint-close evidence, risk carryover, and preload plans. **When to read this:** use at sprint close/open and for async team handoffs.
  - [docs/sprint_handoffs/README.md](sprint_handoffs/README.md)
  - [docs/sprint_handoffs/sprint-handoff-template.md](sprint_handoffs/sprint-handoff-template.md)
  - [docs/sprint_plan_5x.md](sprint_plan_5x.md)
- **Module-local docs** — Deep, code-adjacent docs tied to specific packages/modules. **When to read this:** use when implementing or refactoring inside that specific module.
  - [src/core/README.md](../src/core/README.md)
  - [src/core/ARCHITECTURE.md](../src/core/ARCHITECTURE.md)
  - [src/state_renormalization/README.md](../src/state_renormalization/README.md)
  - [src/semanticng/README.md](../src/semanticng/README.md)

## Source of truth (authoritative files)

Use these as canonical references when conflicts appear:

- `docs/dod_manifest.json` — capability status inventory, ownership paths, and milestone pytest command packs.
- `docs/system_contract_map.md` — contract maturity matrix and transition changelog.
- `docs/release_checklist.md` — release and governance checklist requirements.
- `docs/documentation_change_control.md` — DMAIC routing for required files, validators, and merge blockers.
- `docs/no_regression_budget.json` — no-regression policy and waiver/expiry schema.
- `docs/toolchain_parity_policy.json` — Python/mypy/toolchain parity constants used by docs/scripts/hooks.

## Generated / projection artifacts

Some documentation is generated (fully or partially) from canonical policy/manifests. Edit source-of-truth files first, then regenerate projections.

- `docs/DEVELOPMENT.md` and `docs/dev_toolchain_parity.md` include generated parity blocks.
  - Regenerate with: `python .github/scripts/render_toolchain_parity_docs.py`
  - Source: `docs/toolchain_parity_policy.json`
- `docs/process/script_scope_complexity.md` is a projection artifact emitted by script-complexity analysis.
  - Regenerate with: `python .github/scripts/analyze_script_scope_complexity.py --output docs/process/script_scope_complexity.md`
  - Primary sources: `.github/scripts/*.py`, `docs/process/script_scope_complexity_baseline.json`, `docs/process/script_scope_complexity_waivers.json`
- PR template evidence block is generated (not a `docs/` file but part of governance documentation workflow).
  - Regenerate with: `python .github/scripts/render_transition_evidence.py --regenerate-pr-template`
  - Source: `docs/dod_manifest.json`

When a generated artifact and its source conflict, treat the source file as authoritative and regenerate the artifact.
