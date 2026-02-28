from __future__ import annotations

import difflib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs" / "dod_manifest.json"
PR_TEMPLATE_PATH = ROOT / ".github" / "pull_request_template.md"
SCRIPT_PATH = ROOT / ".github" / "scripts" / "render_transition_evidence.py"

_spec = importlib.util.spec_from_file_location("render_transition_evidence", SCRIPT_PATH)
assert _spec and _spec.loader
render_transition_evidence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render_transition_evidence)


def test_pr_template_autogen_block_matches_generated_output() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    template = PR_TEMPLATE_PATH.read_text(encoding="utf-8")

    start = template.find(render_transition_evidence.AUTOGEN_BEGIN)
    end = template.find(render_transition_evidence.AUTOGEN_END)
    assert start != -1 and end != -1 and end > start, "PR template must include AUTOGEN markers"

    actual_block = template[start : end + len(render_transition_evidence.AUTOGEN_END)]
    expected_block = render_transition_evidence._render_pr_template_autogen_section(manifest)

    if actual_block != expected_block:
        diff = "\n".join(
            difflib.unified_diff(
                actual_block.splitlines(),
                expected_block.splitlines(),
                fromfile="pull_request_template.md (checked in)",
                tofile="pull_request_template.md (generated)",
                lineterm="",
            )
        )
        raise AssertionError(
            "PR template AUTOGEN block is out of date. "
            "Run: python .github/scripts/render_transition_evidence.py --regenerate-pr-template\n"
            f"{diff}"
        )
