#!/usr/bin/env bash
set -euo pipefail

MODE="${PROMOTION_CHECK_SCOPE:-staged}"
DRY_RUN="${PROMOTION_CHECK_DRY_RUN:-0}"

readarray -t STAGED_FILES < <(git diff --cached --name-only --diff-filter=ACMR)

matches_any_path() {
  local path="$1"
  shift
  local candidate
  for candidate in "$@"; do
    if [[ "$path" == "$candidate" || "$path" == "$candidate"/* ]]; then
      return 0
    fi
  done
  return 1
}

scope_touched() {
  local scope="$1"
  shift

  if [[ "$MODE" == "all" ]]; then
    return 0
  fi

  local staged
  for staged in "${STAGED_FILES[@]}"; do
    if matches_any_path "$staged" "$@"; then
      echo "[promotion-check] scope=${scope} triggered-by=${staged}"
      return 0
    fi
  done
  return 1
}

run_check() {
  local scope="$1"
  shift

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[promotion-check] dry-run scope=${scope} cmd=$*"
    return 0
  fi

  echo "[promotion-check] scope=${scope} cmd=$*"
  if ! "$@"; then
    echo
    echo "COMMIT BLOCKED: promotion policy check failed for scope '${scope}'."
    echo "This repository is in a non-promotable state for the staged policy surface."
    echo "Fix the error shown above, then re-run the command locally:"
    echo "  $*"
    exit 1
  fi
}

should_run_milestone_docs=0
if scope_touched "milestone-docs" \
  src/state_renormalization \
  docs/dod_manifest.json \
  docs/release_checklist.md \
  docs/documentation_change_control.md \
  docs/system_contract_map.md \
  docs/sprint_handoffs \
  ROADMAP.md \
  .github/pull_request_template.md \
  .github/scripts/validate_milestone_docs.py \
  .github/scripts/validate_sprint_handoff.py \
  .github/scripts/validate_doc_freshness_slo.py \
  .github/scripts/capability_parity_report.py \
  .github/scripts/render_transition_evidence.py \
  .github/scripts/validate_governance_sync.py \
  .github/scripts/validate_governance_docs_schema.py \
  .github/scripts/run_promotion_checks.sh \
  Makefile \
  .github/workflows/state-renorm-milestone-gate.yml \
  .github/workflows/quality-guardrails.yml \
  .github/actions/python-test-setup/action.yml; then
  should_run_milestone_docs=1
  run_check "milestone-docs" python .github/scripts/validate_milestone_docs.py
  run_check "governance-sync" python .github/scripts/validate_governance_sync.py
  run_check "governance-schema" python .github/scripts/validate_governance_docs_schema.py
  run_check "sprint-handoffs" python .github/scripts/validate_sprint_handoff.py
fi

if scope_touched "doc-freshness-slo" docs src MISSION.md README.md ROADMAP.md; then
  run_check "doc-freshness-slo" python .github/scripts/validate_doc_freshness_slo.py --config docs/doc_freshness_slo.json
fi

if scope_touched "pr-template-autogen" \
  docs/dod_manifest.json \
  docs/system_contract_map.md \
  ROADMAP.md \
  .github/pull_request_template.md \
  .github/scripts/render_transition_evidence.py; then
  run_check "pr-template-autogen" python .github/scripts/render_transition_evidence.py --check-pr-template-autogen

  # Optional generated-content policy: autogen must not introduce additional diffs.
  run_check "pr-template-regeneration" python .github/scripts/render_transition_evidence.py --regenerate-pr-template
  if [[ "$DRY_RUN" != "1" ]] && ! git diff --quiet -- .github/pull_request_template.md; then
    echo "COMMIT BLOCKED: generated PR template content is stale. Run:"
    echo "  python .github/scripts/render_transition_evidence.py --regenerate-pr-template"
    echo "Then commit updated PR template changes."
    git --no-pager diff -- .github/pull_request_template.md
    exit 1
  fi
fi

if [[ "$MODE" != "all" && ${#STAGED_FILES[@]} -eq 0 ]]; then
  echo "No staged files; skipping promotion checks."
elif [[ "$MODE" != "all" && $should_run_milestone_docs -eq 0 ]]; then
  echo "No staged promotion-policy files detected; skipped non-applicable promotion checks."
fi

echo "Promotion checks passed."
