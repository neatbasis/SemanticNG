from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts/ci/check_core_isolation_protocol.py"
SPEC = importlib.util.spec_from_file_location("check_core_isolation_protocol", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_parse_added_lines_tracks_line_numbers() -> None:
    diff = """diff --git a/src/core/example.py b/src/core/example.py
--- a/src/core/example.py
+++ b/src/core/example.py
@@ -0,0 +1,2 @@
+import state_renormalization.engine
+value = 1
"""
    added = MODULE._parse_added_lines(diff)
    assert added == [
        ("src/core/example.py", 1, "import state_renormalization.engine"),
        ("src/core/example.py", 2, "value = 1"),
    ]


def test_detect_forbidden_imports_flags_state_renormalization() -> None:
    violations = MODULE._detect_forbidden_imports(
        [("src/core/example.py", 7, "from state_renormalization.engine import run")]
    )
    assert len(violations) == 1
    assert violations[0].code == "CIP-FORBIDDEN-IMPORT"


def test_detect_orchestration_markers_flags_workflow_language() -> None:
    violations = MODULE._detect_orchestration_markers(
        [("src/core/example.md", 12, "Defines workflow sequencing semantics")]
    )
    assert len(violations) == 1
    assert violations[0].code == "CIP-ORCHESTRATION-LEAK"
