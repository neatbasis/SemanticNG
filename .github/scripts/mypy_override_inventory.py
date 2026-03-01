#!/usr/bin/env python3
"""Emit an inventory of mypy suppressions configured in pyproject.toml overrides."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import tomllib

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PYPROJECT = ROOT / "pyproject.toml"


def _load_overrides(pyproject_path: Path) -> list[dict[str, Any]]:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    tool = data.get("tool")
    if not isinstance(tool, dict):
        return []
    mypy = tool.get("mypy")
    if not isinstance(mypy, dict):
        return []
    overrides = mypy.get("overrides")
    if not isinstance(overrides, list):
        return []
    return [item for item in overrides if isinstance(item, dict)]


def _suppression_rows(overrides: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for idx, override in enumerate(overrides, start=1):
        modules = override.get("module")
        if isinstance(modules, str):
            module_list = [modules]
        elif isinstance(modules, list):
            module_list = [str(module) for module in modules]
        else:
            module_list = ["<unknown>"]

        for key, value in override.items():
            if key == "module":
                continue
            if value is not False:
                continue
            for module in module_list:
                rows.append(
                    {
                        "override_index": str(idx),
                        "module": module,
                        "suppression": f"{key} = false",
                    }
                )
    return rows


def _format_markdown(rows: list[dict[str, str]]) -> str:
    header = "| Override # | Module | Suppression |\n| --- | --- | --- |"
    body = [f"| {r['override_index']} | `{r['module']}` | `{r['suppression']}` |" for r in rows]
    return "\n".join([header, *body])


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=DEFAULT_PYPROJECT,
        help="Path to pyproject.toml (default: repository root pyproject.toml).",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format for suppression inventory.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    overrides = _load_overrides(args.pyproject)
    rows = _suppression_rows(overrides)

    if args.format == "json":
        print(json.dumps(rows, indent=2))
    else:
        print(_format_markdown(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
