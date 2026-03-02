#!/usr/bin/env bash
set -euo pipefail

# Apply the CI-generated pre-commit autofix patch artifact locally.
#
# Usage:
#   scripts/ci/apply_precommit_patch.sh /path/to/precommit_autofix.patch
#
# Typical flow:
#   1. Download the `precommit-autofix-patch` artifact from CI.
#   2. Run this script with the downloaded patch path.
#   3. Re-run `pre-commit run --all-files` to validate clean output.
#   4. Commit the resulting changes.

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/precommit_autofix.patch" >&2
  exit 1
fi

patch_file="$1"

if [[ ! -f "$patch_file" ]]; then
  echo "Patch file not found: $patch_file" >&2
  exit 1
fi

echo "Applying patch: $patch_file"
git apply --index "$patch_file"

echo "Patch applied. Validate with: pre-commit run --all-files"
echo "Then commit with: git commit -m 'Apply pre-commit fixes'"
