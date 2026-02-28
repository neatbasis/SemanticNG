#!/usr/bin/env bash
set -euo pipefail

python .github/scripts/validate_milestone_docs.py
python .github/scripts/render_transition_evidence.py --check-pr-template-autogen

# Optional generated-content policy: autogen must not introduce additional diffs.
python .github/scripts/render_transition_evidence.py --regenerate-pr-template
if ! git diff --quiet -- .github/pull_request_template.md; then
  echo "Generated PR template content is stale. Run:"
  echo "  python .github/scripts/render_transition_evidence.py --regenerate-pr-template"
  echo "Then commit updated PR template changes."
  git --no-pager diff -- .github/pull_request_template.md
  exit 1
fi

echo "Promotion checks passed."
