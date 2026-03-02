# .github/scripts scope-alignment and complexity report

This report is static analysis only. Scope is inferred from script naming and call sites in pre-commit/Makefile/workflows.

| Script | Inferred scope | Referenced by | LOC | Functions | Complexity (approx) |
| --- | --- | --- | ---: | ---: | ---: |
| `.github/scripts/aggregate_precommit_failure_learning.py` | quality-analytics | .github/workflows/precommit-learning-loop-weekly.yml | 101 | 5 | 18 |
| `.github/scripts/analyze_script_scope_complexity.py` | general-governance | .github/workflows/quality-guardrails.yml | 129 | 7 | 20 |
| `.github/scripts/audit_branch_protection.py` | governance-audit | .github/workflows/branch-protection-audit.yml | 170 | 7 | 48 |
| `.github/scripts/capability_parity_report.py` | general-governance | .github/workflows/state-renorm-milestone-gate.yml | 444 | 21 | 131 |
| `.github/scripts/check_no_regression_budget.py` | guardrail-check | .github/workflows/quality-guardrails.yml | 77 | 6 | 21 |
| `.github/scripts/check_precommit_parity.py` | guardrail-check | Makefile, .github/workflows/toolchain-parity-weekly.yml | 255 | 15 | 54 |
| `.github/scripts/check_python_support_policy.py` | guardrail-check | Makefile, .github/workflows/state-renorm-milestone-gate.yml, .github/workflows/toolchain-parity-weekly.yml | 67 | 4 | 10 |
| `.github/scripts/check_root_scratch_files.py` | guardrail-check | Makefile | 57 | 4 | 9 |
| `.github/scripts/classify_precommit_failures.py` | quality-diagnostics | .github/workflows/quality-guardrails.yml | 163 | 4 | 28 |
| `.github/scripts/mypy_override_inventory.py` | general-governance | unreferenced | 135 | 8 | 41 |
| `.github/scripts/print_env_provenance.py` | general-governance | Makefile, .github/workflows/state-renorm-milestone-gate.yml | 37 | 2 | 4 |
| `.github/scripts/reliability_report.py` | general-governance | unreferenced | 401 | 18 | 87 |
| `.github/scripts/render_toolchain_parity_docs.py` | evidence-rendering | unreferenced | 43 | 3 | 6 |
| `.github/scripts/render_transition_evidence.py` | evidence-rendering | .github/workflows/state-renorm-milestone-gate.yml | 240 | 14 | 49 |
| `.github/scripts/required_check_sentinel.py` | general-governance | .github/workflows/required-check-regression-sentinel.yml | 52 | 2 | 9 |
| `.github/scripts/run_hook_parity_with_diagnostics.py` | execution-orchestration | Makefile | 44 | 1 | 5 |
| `.github/scripts/run_precommit_governance_checks.py` | execution-orchestration | unreferenced | 114 | 7 | 33 |
| `.github/scripts/run_promotion_checks.sh` | execution-orchestration | .pre-commit-config.yaml, Makefile, .github/workflows/state-renorm-milestone-gate.yml | 31 | 1 | 5 |
| `.github/scripts/select_milestone_test_commands.py` | test-surface-selection | .github/workflows/state-renorm-milestone-gate.yml | 186 | 11 | 42 |
| `.github/scripts/validate_doc_freshness_slo.py` | policy-validation | .github/workflows/state-renorm-milestone-gate.yml | 336 | 13 | 73 |
| `.github/scripts/validate_governance_docs_schema.py` | policy-validation | .github/workflows/state-renorm-milestone-gate.yml | 98 | 5 | 34 |
| `.github/scripts/validate_governance_sync.py` | policy-validation | .github/workflows/state-renorm-milestone-gate.yml | 217 | 12 | 62 |
| `.github/scripts/validate_milestone_docs.py` | policy-validation | .github/workflows/state-renorm-milestone-gate.yml | 718 | 32 | 211 |
| `.github/scripts/validate_no_regression_budget_update.py` | policy-validation | .github/workflows/quality-guardrails.yml | 149 | 9 | 42 |
| `.github/scripts/validate_sprint_handoff.py` | policy-validation | .github/workflows/state-renorm-milestone-gate.yml | 172 | 9 | 54 |

- Script count: **25**
- Total non-empty LOC: **4436**
- Total approximate complexity: **1096**
