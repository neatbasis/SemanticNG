#!/usr/bin/env bash
set -euo pipefail

mapfile -t STAGED_FILES < <(git diff --cached --name-only --diff-filter=ACMR)

matches_scope() {
  local path="$1"
  shift
  local pattern
  for pattern in "$@"; do
    if [[ "$path" == $pattern ]]; then
      return 0
    fi
  done
  return 1
}

collect_scope_reasons() {
  local -n _out_reasons=$1
  shift
  local pattern_list=("$@")
  local staged
  for staged in "${STAGED_FILES[@]}"; do
    if matches_scope "$staged" "${pattern_list[@]}"; then
      _out_reasons+=("${staged}")
    fi
  done
}

run_check() {
  local scope="$1"
  local reason="$2"
  shift 2
  echo "[promotion-check] scope=${scope} reason=${reason} cmd=$*"
  if ! "$@"; then
    echo
    echo "COMMIT BLOCKED: promotion policy check failed for scope '${scope}'."
    echo "This repository is in a non-promotable state for the staged policy surface."
    echo "Check triggered because: ${reason}"
    echo "Fix the error shown above, then re-run the command locally:"
    echo "  $*"
    exit 1
  fi
}

GOVERNANCE_PATTERNS=(
  "docs/dod_manifest.json"
  "docs/milestones/*"
  "docs/governance/*"
  ".github/scripts/validate_milestone_docs.py"
  ".github/scripts/validate_governance_sync.py"
  ".github/scripts/validate_governance_docs_schema.py"
  ".github/scripts/validate_sprint_handoff.py"
  ".github/workflows/*"
)

FRESHNESS_PATTERNS=(
  "docs/doc_freshness_slo.json"
  "docs/release_checklist.md"
  "docs/documentation_change_control.md"
  "docs/sprint_handoffs/*"
  "docs/system_contract_map.md"
  "ROADMAP.md"
  ".github/scripts/validate_doc_freshness_slo.py"
)

PR_TEMPLATE_PATTERNS=(
  "docs/dod_manifest.json"
  ".github/pull_request_template.md"
  ".github/scripts/render_transition_evidence.py"
)

BOUNDARY_PATTERNS=(
  "src/core/**"
  "src/state_renormalization/**"
  "src/semanticng/**"
)

BOUNDARY_CONTRACT_DOC_PATTERNS=(
  "docs/system_contract_map.md"
  "docs/dod_manifest.json"
  "docs/definition_of_complete.md"
  "docs/documentation_change_control.md"
)

governance_reasons=()
freshness_reasons=()
pr_template_reasons=()
boundary_reasons=()
boundary_contract_doc_reasons=()

collect_scope_reasons governance_reasons "${GOVERNANCE_PATTERNS[@]}"
collect_scope_reasons freshness_reasons "${FRESHNESS_PATTERNS[@]}"
collect_scope_reasons pr_template_reasons "${PR_TEMPLATE_PATTERNS[@]}"
collect_scope_reasons boundary_reasons "${BOUNDARY_PATTERNS[@]}"
collect_scope_reasons boundary_contract_doc_reasons "${BOUNDARY_CONTRACT_DOC_PATTERNS[@]}"

if [[ ${#governance_reasons[@]} -eq 0 && ${#freshness_reasons[@]} -eq 0 && ${#pr_template_reasons[@]} -eq 0 && ${#boundary_reasons[@]} -eq 0 ]]; then
  echo "Promotion checks skipped: no staged files touched promotion policy surfaces."
  if [[ ${#STAGED_FILES[@]} -gt 0 ]]; then
    printf 'Staged files (non-policy):\n'
    printf '  - %s\n' "${STAGED_FILES[@]}"
  fi
  exit 0
fi

if [[ ${#governance_reasons[@]} -gt 0 ]]; then
  gov_reason="matched staged path(s): $(printf '%s, ' "${governance_reasons[@]}")"
  gov_reason="${gov_reason%, }"
  run_check "milestone-docs" "$gov_reason" python .github/scripts/validate_milestone_docs.py
  run_check "governance-sync" "$gov_reason" python .github/scripts/validate_governance_sync.py
  run_check "governance-schema" "$gov_reason" python .github/scripts/validate_governance_docs_schema.py
  run_check "sprint-handoffs" "$gov_reason" python .github/scripts/validate_sprint_handoff.py
fi

if [[ ${#freshness_reasons[@]} -gt 0 ]]; then
  freshness_reason="matched staged path(s): $(printf '%s, ' "${freshness_reasons[@]}")"
  freshness_reason="${freshness_reason%, }"
  run_check "doc-freshness-slo" "$freshness_reason" python .github/scripts/validate_doc_freshness_slo.py --config docs/doc_freshness_slo.json
fi

if [[ ${#pr_template_reasons[@]} -gt 0 ]]; then
  pr_reason="matched staged path(s): $(printf '%s, ' "${pr_template_reasons[@]}")"
  pr_reason="${pr_reason%, }"
  run_check "pr-template-autogen" "$pr_reason" python .github/scripts/render_transition_evidence.py --check-pr-template-autogen

  # Optional generated-content policy: autogen must not introduce additional diffs.
  run_check "pr-template-regeneration" "$pr_reason" python .github/scripts/render_transition_evidence.py --regenerate-pr-template
  if ! git diff --quiet -- .github/pull_request_template.md; then
    echo "COMMIT BLOCKED: generated PR template content is stale."
    echo "Check triggered because: ${pr_reason}"
    echo "Run:"
    echo "  python .github/scripts/render_transition_evidence.py --regenerate-pr-template"
    echo "Then commit updated PR template changes."
    git --no-pager diff -- .github/pull_request_template.md
    exit 1
  fi
fi


if [[ ${#boundary_reasons[@]} -gt 0 && ${#boundary_contract_doc_reasons[@]} -eq 0 ]]; then
  boundary_reason="matched semantic boundary staged path(s): $(printf '%s, ' "${boundary_reasons[@]}")"
  boundary_reason="${boundary_reason%, }"
  echo "COMMIT BLOCKED: semantic boundary contract updates are required."
  echo "Check triggered because: ${boundary_reason}"
  echo "Also stage at least one matching governance/contract doc update:"
  printf '  - %s
' "${BOUNDARY_CONTRACT_DOC_PATTERNS[@]}"
  echo "Then re-run: make promotion-governance-check"
  exit 1
fi

echo "Promotion checks passed."
