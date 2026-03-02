#!/usr/bin/env python3
"""Measure .github/scripts scope alignment and static complexity."""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class ScriptMetrics:
    path: Path
    scope: str
    referenced_by: list[str]
    loc: int
    complexity: int
    funcs: int


@dataclass
class ThresholdBreach:
    metric: str
    subject: str
    actual: int
    limit: int
    waived: bool
    waiver_reason: str | None = None


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


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def waiver_lookup(waivers: list[dict], metric: str, subject: str) -> tuple[bool, str | None]:
    today = date.today()
    for waiver in waivers:
        waiver_metric = waiver.get('metric', '').strip()
        waiver_subject = waiver.get('subject', '').strip()
        if waiver_metric != metric or waiver_subject != subject:
            continue
        expires_on = waiver.get('expires_on', '').strip()
        reason = waiver.get('reason', '').strip() or 'no reason provided'
        try:
            expiry = date.fromisoformat(expires_on)
        except ValueError:
            return False, f'invalid expiry format: {expires_on!r}'
        if expiry < today:
            return False, f'waiver expired on {expires_on}: {reason}'
        return True, f'waived until {expires_on}: {reason}'
    return False, None


def evaluate_thresholds(
    metrics: list[ScriptMetrics],
    *,
    baseline: dict,
    waivers: list[dict],
    max_script_complexity: int | None,
    max_total_complexity_delta: int | None,
) -> list[ThresholdBreach]:
    breaches: list[ThresholdBreach] = []
    for metric in metrics:
        if max_script_complexity is None:
            continue
        if metric.complexity <= max_script_complexity:
            continue
        waived, waiver_reason = waiver_lookup(waivers, 'script-complexity', str(metric.path))
        breaches.append(
            ThresholdBreach(
                metric='script-complexity',
                subject=str(metric.path),
                actual=metric.complexity,
                limit=max_script_complexity,
                waived=waived,
                waiver_reason=waiver_reason,
            )
        )

    baseline_total_complexity = int(baseline.get('total_complexity', 0))
    total_complexity = sum(metric.complexity for metric in metrics)
    total_delta = total_complexity - baseline_total_complexity
    if max_total_complexity_delta is not None and total_delta > max_total_complexity_delta:
        waived, waiver_reason = waiver_lookup(waivers, 'total-complexity-delta', 'all-scripts')
        breaches.append(
            ThresholdBreach(
                metric='total-complexity-delta',
                subject='all-scripts',
                actual=total_delta,
                limit=max_total_complexity_delta,
                waived=waived,
                waiver_reason=waiver_reason,
            )
        )
    return breaches


def render_report(
    metrics: list[ScriptMetrics],
    *,
    baseline: dict,
    max_script_complexity: int | None,
    max_total_complexity_delta: int | None,
    breaches: list[ThresholdBreach],
) -> str:
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

    baseline_total_complexity = int(baseline.get('total_complexity', 0))
    total_delta = total_complexity - baseline_total_complexity
    lines.extend([
        f'- Baseline total complexity: **{baseline_total_complexity}**',
        f'- Total complexity delta vs baseline: **{total_delta}**',
    ])

    lines.extend([
        '',
        '## Threshold evaluation',
        f'- Max per-script complexity threshold: **{max_script_complexity if max_script_complexity is not None else "disabled"}**',
        f'- Max total complexity delta threshold: **{max_total_complexity_delta if max_total_complexity_delta is not None else "disabled"}**',
    ])
    if not breaches:
        lines.append('- Result: ✅ no threshold breaches detected.')
    else:
        lines.append('- Result: ❌ threshold breaches detected (waived breaches are informational).')
        lines.extend([
            '',
            '| Metric | Subject | Actual | Limit | Status | Details |',
            '| --- | --- | ---: | ---: | --- | --- |',
        ])
        for breach in breaches:
            status = 'waived' if breach.waived else 'active breach'
            detail = breach.waiver_reason or ''
            lines.append(
                f'| {breach.metric} | `{breach.subject}` | {breach.actual} | {breach.limit} | {status} | {detail} |'
            )
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='artifacts/script_scope_complexity.md')
    parser.add_argument('--baseline-file', default='docs/process/script_scope_complexity_baseline.json')
    parser.add_argument('--waiver-file', default='docs/process/script_scope_complexity_waivers.json')
    parser.add_argument('--max-script-complexity', type=int, default=None)
    parser.add_argument('--max-total-complexity-delta', type=int, default=None)
    parser.add_argument('--check', action='store_true', help='fail if active threshold breaches are detected')
    args = parser.parse_args()

    baseline = load_json(Path(args.baseline_file))
    waivers = load_json(Path(args.waiver_file)).get('waivers', [])
    metrics = collect_metrics()
    breaches = evaluate_thresholds(
        metrics,
        baseline=baseline,
        waivers=waivers,
        max_script_complexity=args.max_script_complexity,
        max_total_complexity_delta=args.max_total_complexity_delta,
    )
    report = render_report(
        metrics,
        baseline=baseline,
        max_script_complexity=args.max_script_complexity,
        max_total_complexity_delta=args.max_total_complexity_delta,
        breaches=breaches,
    )
    out = Path(args.output)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding='utf-8')
    print(f'Wrote {out}')
    active_breaches = [breach for breach in breaches if not breach.waived]
    if args.check and active_breaches:
        print('Threshold breaches detected:')
        for breach in active_breaches:
            print(
                f"- {breach.metric} on {breach.subject}: actual={breach.actual} limit={breach.limit}"
            )
            if breach.waiver_reason:
                print(f'  details: {breach.waiver_reason}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
