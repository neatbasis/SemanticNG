#!/usr/bin/env bash
set -euo pipefail

run_check() {
  local scope="$1"
  shift
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

run_check "milestone-docs" python .github/scripts/validate_milestone_docs.py
run_check "governance-sync" python .github/scripts/validate_governance_sync.py
run_check "governance-schema" python .github/scripts/validate_governance_docs_schema.py
run_check "sprint-handoffs" python .github/scripts/validate_sprint_handoff.py
run_check "doc-freshness-slo" python .github/scripts/validate_doc_freshness_slo.py --config docs/doc_freshness_slo.json
run_check "pr-template-autogen" python .github/scripts/render_transition_evidence.py --check-pr-template-autogen

# Optional generated-content policy: autogen must not introduce additional diffs.
run_check "pr-template-regeneration" python .github/scripts/render_transition_evidence.py --regenerate-pr-template
if ! git diff --quiet -- .github/pull_request_template.md; then
  echo "COMMIT BLOCKED: generated PR template content is stale. Run:"
  echo "  python .github/scripts/render_transition_evidence.py --regenerate-pr-template"
  echo "Then commit updated PR template changes."
  git --no-pager diff -- .github/pull_request_template.md
  exit 1
fi

echo "Promotion checks passed."
