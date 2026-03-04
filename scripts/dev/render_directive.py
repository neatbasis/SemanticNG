from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def render_markdown(record: dict[str, Any]) -> str:
    supersedes = _as_list(record.get("supersedes"))
    canonical_refs = _as_list(record.get("canonical_refs"))
    evidence_commands = _as_list(record.get("evidence_commands"))
    owners = _as_list(record.get("owners"))

    lines = [
        f"# {record.get('id', 'UNKNOWN')}: {record.get('title', '')}",
        "",
        "## Metadata",
        "",
        f"- **Status:** {record.get('status', '')}",
        f"- **Date:** {record.get('date', '')}",
        f"- **Owners:** {', '.join(owners)}",
        f"- **CI policy:** {record.get('ci_policy', '')}",
        (
            f"- **Supersedes:** {', '.join(supersedes)}"
            if supersedes
            else "- **Supersedes:** none"
        ),
        "",
        "## Context",
        "",
        str(record.get("context", "")),
        "",
        "## Decision",
        "",
        str(record.get("decision", "")),
        "",
        "## Consequences",
        "",
        str(record.get("consequences", "")),
        "",
        "## Canonical references",
        "",
    ]

    lines.extend(f"- `{item}`" for item in canonical_refs)
    lines.extend(["", "## Evidence commands", ""])
    lines.extend(f"- `{item}`" for item in evidence_commands)
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render directive JSON into a markdown companion")
    parser.add_argument("source", type=Path, help="Path to directive JSON file")
    parser.add_argument("--output", type=Path, help="Output markdown path; defaults next to source")
    args = parser.parse_args()

    source_path = args.source
    record = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("directive JSON must be an object")

    output_path = args.output or source_path.with_suffix(".md")
    output_path.write_text(render_markdown(record), encoding="utf-8")
    print(f"Rendered {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
