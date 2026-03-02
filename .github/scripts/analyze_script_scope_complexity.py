#!/usr/bin/env python3
"""Measure .github/scripts scope alignment and static complexity."""

from __future__ import annotations

import argparse
import ast
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScriptMetrics:
    path: Path
    scope: str
    referenced_by: list[str]
    loc: int
    complexity: int
    funcs: int


SCOPE_HINTS: list[tuple[str, str]] = [
    ("validate_", "policy-validation"),
    ("check_", "guardrail-check"),
    ("render_", "evidence-rendering"),
    ("audit_", "governance-audit"),
    ("select_", "test-surface-selection"),
    ("run_", "execution-orchestration"),
    ("classify_", "quality-diagnostics"),
    ("aggregate_", "quality-analytics"),
]


def infer_scope(name: str) -> str:
    for prefix, scope in SCOPE_HINTS:
        if name.startswith(prefix):
            return scope
    return "general-governance"


def py_complexity(path: Path, source: str) -> tuple[int, int]:
    tree = ast.parse(source)
    funcs = 0
    branches = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs += 1
        if isinstance(
            node,
            (
                ast.If,
                ast.For,
                ast.AsyncFor,
                ast.While,
                ast.Try,
                ast.With,
                ast.BoolOp,
                ast.IfExp,
                ast.Match,
                ast.comprehension,
            ),
        ):
            branches += 1
    return funcs, branches


def sh_complexity(source: str) -> tuple[int, int]:
    funcs = len(re.findall(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*\(\)\s*\{", source, flags=re.M))
    branches = 1 + len(re.findall(r"\b(if|for|while|case|&&|\|\|)\b", source))
    return funcs, branches


def find_references(script_name: str) -> list[str]:
    refs: list[str] = []
    for path in [Path('.pre-commit-config.yaml'), Path('Makefile'), *Path('.github/workflows').glob('*.yml')]:
        if not path.exists():
            continue
        text = path.read_text(encoding='utf-8')
        if script_name in text:
            refs.append(str(path))
    return refs


def collect_metrics() -> list[ScriptMetrics]:
    metrics: list[ScriptMetrics] = []
    for path in sorted(Path('.github/scripts').glob('*')):
        if path.suffix not in {'.py', '.sh'}:
            continue
        source = path.read_text(encoding='utf-8')
        loc = sum(1 for line in source.splitlines() if line.strip())
        if path.suffix == '.py':
            funcs, complexity = py_complexity(path, source)
        else:
            funcs, complexity = sh_complexity(source)
        metrics.append(
            ScriptMetrics(
                path=path,
                scope=infer_scope(path.stem),
                referenced_by=find_references(path.name),
                loc=loc,
                complexity=complexity,
                funcs=funcs,
            )
        )
    return metrics


def render_report(metrics: list[ScriptMetrics]) -> str:
    lines = [
        '# .github/scripts scope-alignment and complexity report',
        '',
        'This report is static analysis only. Scope is inferred from script naming and call sites in pre-commit/Makefile/workflows.',
        '',
        '| Script | Inferred scope | Referenced by | LOC | Functions | Complexity (approx) |',
        '| --- | --- | --- | ---: | ---: | ---: |',
    ]
    for m in metrics:
        refs = ', '.join(m.referenced_by) if m.referenced_by else 'unreferenced'
        lines.append(
            f'| `{m.path}` | {m.scope} | {refs} | {m.loc} | {m.funcs} | {m.complexity} |'
        )
    total_loc = sum(m.loc for m in metrics)
    total_complexity = sum(m.complexity for m in metrics)
    lines.extend([
        '',
        f'- Script count: **{len(metrics)}**',
        f'- Total non-empty LOC: **{total_loc}**',
        f'- Total approximate complexity: **{total_complexity}**',
    ])
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='artifacts/script_scope_complexity.md')
    parser.add_argument('--check', action='store_true', help='fail if output differs from existing file')
    args = parser.parse_args()

    report = render_report(collect_metrics())
    out = Path(args.output)
    if args.check and out.exists() and out.read_text(encoding='utf-8') != report:
        print(f'Report drift detected in {out}. Re-generate and commit updated report.')
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding='utf-8')
    print(f'Wrote {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
