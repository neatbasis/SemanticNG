from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
REQUIRED_ORCHESTRATOR_MARKER = "# topology-role: required-orchestrator"


def find_required_orchestrators(workflow_dir: Path) -> list[Path]:
    orchestrators: list[Path] = []
    for workflow_file in sorted(workflow_dir.glob("*.yml")):
        text = workflow_file.read_text(encoding="utf-8")
        if REQUIRED_ORCHESTRATOR_MARKER in text:
            orchestrators.append(workflow_file)
    return orchestrators


def validate_workflow_topology(workflow_dir: Path = WORKFLOW_DIR) -> list[str]:
    issues: list[str] = []
    orchestrators = find_required_orchestrators(workflow_dir)

    if len(orchestrators) != 1:
        listed = ", ".join(path.name for path in orchestrators) or "none"
        issues.append(
            "expected exactly one required orchestrator workflow "
            f"marked with '{REQUIRED_ORCHESTRATOR_MARKER}', found {len(orchestrators)} ({listed})"
        )
    return issues


def main() -> int:
    issues = validate_workflow_topology()
    if issues:
        print("Workflow topology validation failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    orchestrator = find_required_orchestrators(WORKFLOW_DIR)[0]
    print(
        "Workflow topology validation passed. "
        f"Required orchestrator: {orchestrator.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
