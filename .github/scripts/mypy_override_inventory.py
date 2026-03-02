#!/usr/bin/env python3
"""Emit an inventory of mypy suppressions configured in pyproject.toml overrides."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import re

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10 CI
    tomllib = None

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PYPROJECT = ROOT / "pyproject.toml"


def _parse_bool(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return None


def _parse_module_value(raw: str) -> str | list[str] | None:
    value = raw.strip()
    if value.startswith("[") and value.endswith("]"):
        return [module for module in re.findall(r'"([^"\n]+)"', value)]
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return None


def _load_overrides_without_tomllib(pyproject_path: Path) -> list[dict[str, Any]]:
    text = pyproject_path.read_text(encoding="utf-8")
    blocks = text.split("[[tool.mypy.overrides]]")
    if len(blocks) <= 1:
        return []

    overrides: list[dict[str, Any]] = []
    for block in blocks[1:]:
        section = block.split("[[", 1)[0].split("[tool.", 1)[0]
        lines = [line.split("#", 1)[0].rstrip() for line in section.splitlines()]
        override: dict[str, Any] = {}

        idx = 0
        while idx < len(lines):
            line = lines[idx].strip()
            idx += 1
            if not line or "=" not in line:
                continue
            key, raw = [part.strip() for part in line.split("=", 1)]

            if key == "module" and raw.startswith("[") and not raw.rstrip().endswith("]"):
                chunks = [raw]
                while idx < len(lines):
                    nxt = lines[idx].strip()
                    idx += 1
                    if not nxt:
                        continue
                    chunks.append(nxt)
                    if nxt.endswith("]"):
                        break
                raw = " ".join(chunks)

            if key == "module":
                parsed_module = _parse_module_value(raw)
                if parsed_module is not None:
                    override[key] = parsed_module
                continue

            parsed_bool = _parse_bool(raw)
            if parsed_bool is not None:
                override[key] = parsed_bool

        if override:
            overrides.append(override)

    return overrides


def _load_overrides(pyproject_path: Path) -> list[dict[str, Any]]:
    if tomllib is None:
        return _load_overrides_without_tomllib(pyproject_path)

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
