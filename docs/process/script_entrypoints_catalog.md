# Script entrypoints catalog

Catalog generated from `docs/process/script_entrypoints_inventory.json`.

| Script path | Purpose | Invocation source(s) | Owning workflow/check | Documentation link |
| --- | --- | --- | --- | --- |
| `.github/scripts/aggregate_precommit_failure_learning.py` | Python automation entrypoint. | filesystem_scan<br>workflow:.github/workflows/precommit-learning-loop-weekly.yml:L28 | workflow:precommit-learning-loop-weekly | MISSING_DOC |
| `.github/scripts/analyze_script_scope_complexity.py` | Python automation entrypoint. | filesystem_scan<br>workflow:.github/workflows/quality-guardrails.yml:L65 | workflow:quality-guardrails | MISSING_DOC |
| `.github/scripts/audit_branch_protection.py` | Python automation entrypoint. | filesystem_scan<br>workflow:.github/workflows/branch-protection-audit.yml:L22 | workflow:branch-protection-audit | MISSING_DOC |
| `.github/scripts/capability_parity_report.py` | Python automation entrypoint. | filesystem_scan |  | MISSING_DOC |
| `.github/scripts/check_no_regression_budget.py` | Python automation entrypoint. | filesystem_scan<br>quality_stage:qa-ci:commands[0]<br>workflow:.github/workflows/quality-guardrails.yml:L103 | quality_stage:qa-ci<br>workflow:quality-guardrails | MISSING_DOC |
| `.github/scripts/check_precommit_parity.py` | Python automation entrypoint. | filesystem_scan<br>make:qa-hook-parity:L38<br>workflow:.github/workflows/toolchain-parity-weekly.yml:L33 | make:qa-hook-parity<br>workflow:toolchain-parity-weekly | MISSING_DOC |
| `.github/scripts/check_python_support_policy.py` | Python automation entrypoint. | filesystem_scan<br>make:qa-hook-parity:L37<br>workflow:.github/workflows/state-renorm-milestone-gate.yml:L89<br>workflow:.github/workflows/toolchain-parity-weekly.yml:L27 | make:qa-hook-parity<br>workflow:state-renorm-milestone-gate<br>workflow:toolchain-parity-weekly | MISSING_DOC |
| `.github/scripts/check_root_scratch_files.py` | Python automation entrypoint. | filesystem_scan<br>make:scratch-hygiene:L61 | make:scratch-hygiene | MISSING_DOC |
| `.github/scripts/classify_precommit_failures.py` | Python automation entrypoint. | filesystem_scan<br>workflow:.github/workflows/quality-guardrails.yml:L139 | workflow:quality-guardrails | MISSING_DOC |
| `.github/scripts/inventory_script_entrypoints.py` | Python automation entrypoint. | filesystem_scan |  | MISSING_DOC |
| `.github/scripts/mypy_override_inventory.py` | Python automation entrypoint. | filesystem_scan |  | MISSING_DOC |
| `.github/scripts/print_env_provenance.py` | Python automation entrypoint. | filesystem_scan<br>make:setup-dev:L14<br>workflow:.github/workflows/state-renorm-milestone-gate.yml:L95 | make:setup-dev<br>workflow:state-renorm-milestone-gate | MISSING_DOC |
| `.github/scripts/reliability_report.py` | Python automation entrypoint. | filesystem_scan |  | MISSING_DOC |
| `.github/scripts/render_toolchain_parity_docs.py` | Python automation entrypoint. | filesystem_scan |  | MISSING_DOC |
| `.github/scripts/render_transition_evidence.py` | Python automation entrypoint. | filesystem_scan<br>workflow:.github/workflows/state-renorm-milestone-gate.yml:L142<br>workflow:.github/workflows/state-renorm-milestone-gate.yml:L154 | workflow:state-renorm-milestone-gate | MISSING_DOC |
| `.github/scripts/required_check_sentinel.py` | Python automation entrypoint. | filesystem_scan<br>workflow:.github/workflows/required-check-regression-sentinel.yml:L27 | workflow:required-check-regression-sentinel | MISSING_DOC |
| `.github/scripts/run_hook_parity_with_diagnostics.py` | Python automation entrypoint. | filesystem_scan<br>make:qa-hook-parity-diagnostics:L42 | make:qa-hook-parity-diagnostics | MISSING_DOC |
| `.github/scripts/run_precommit_governance_checks.py` | Python automation entrypoint. | filesystem_scan<br>precommit:precommit-governance-selector:L52 | precommit:precommit-governance-selector | MISSING_DOC |
| `.github/scripts/run_promotion_checks.sh` | Shell automation entrypoint. | filesystem_scan<br>make:promotion-governance-check:L64<br>precommit:promotion-governance-pokayoke:L60 | make:promotion-governance-check<br>precommit:promotion-governance-pokayoke | MISSING_DOC |
| `.github/scripts/select_milestone_test_commands.py` | Python automation entrypoint. | filesystem_scan<br>workflow:.github/workflows/state-renorm-milestone-gate.yml:L196 | workflow:state-renorm-milestone-gate | MISSING_DOC |
| `.github/scripts/validate_doc_freshness_slo.py` | Python automation entrypoint. | filesystem_scan |  | MISSING_DOC |
| `.github/scripts/validate_governance_docs_schema.py` | Python automation entrypoint. | filesystem_scan |  | MISSING_DOC |
| `.github/scripts/validate_governance_sync.py` | Python automation entrypoint. | filesystem_scan |  | MISSING_DOC |
| `.github/scripts/validate_milestone_docs.py` | Python automation entrypoint. | filesystem_scan |  | MISSING_DOC |
| `.github/scripts/validate_no_regression_budget_update.py` | Python automation entrypoint. | filesystem_scan<br>workflow:.github/workflows/quality-guardrails.yml:L100 | workflow:quality-guardrails | MISSING_DOC |
| `.github/scripts/validate_sprint_handoff.py` | Python automation entrypoint. | filesystem_scan |  | MISSING_DOC |
| `Makefile:promotion-check` | Makefile quality/workflow target entrypoint. | workflow:.github/workflows/state-renorm-milestone-gate.yml:L177 | workflow:state-renorm-milestone-gate | MISSING_DOC |
| `Makefile:qa-baseline` | Makefile quality/workflow target entrypoint. | workflow:.github/workflows/quality-guardrails.yml:L123 | workflow:quality-guardrails | MISSING_DOC |
| `Makefile:qa-ci` | Makefile quality/workflow target entrypoint. | make:qa-ci-equivalent:L56 | make:qa-ci-equivalent | MISSING_DOC |
| `Makefile:qa-full-type` | Makefile quality/workflow target entrypoint. | workflow:.github/workflows/quality-guardrails.yml:L360 | workflow:quality-guardrails | MISSING_DOC |
| `Makefile:qa-full-type-surface` | Makefile quality/workflow target entrypoint. | make:qa-full-type:L50 | make:qa-full-type | MISSING_DOC |
| `Makefile:qa-hook-parity` | Makefile quality/workflow target entrypoint. | workflow:.github/workflows/state-renorm-milestone-gate.yml:L98 | workflow:state-renorm-milestone-gate | MISSING_DOC |
| `Makefile:qa-push` | Makefile quality/workflow target entrypoint. | make:qa-baseline:L34 | make:qa-baseline | MISSING_DOC |
| `Makefile:qa-test-cov` | Makefile quality/workflow target entrypoint. | make:test-cov:L74<br>workflow:.github/workflows/quality-guardrails.yml:L340<br>workflow:.github/workflows/state-renorm-milestone-gate.yml:L101 | make:test-cov<br>workflow:quality-guardrails<br>workflow:state-renorm-milestone-gate | MISSING_DOC |
| `Makefile:verify-precommit-installed` | Makefile quality/workflow target entrypoint. | make:setup-dev:L9 | make:setup-dev | MISSING_DOC |
| `hook:precommit-governance-selector` | Pre-commit hook entrypoint. | precommit:precommit-governance-selector:L52 | precommit:precommit-governance-selector | MISSING_DOC |
| `hook:promotion-governance-pokayoke` | Pre-commit hook entrypoint. | precommit:promotion-governance-pokayoke:L60 | precommit:promotion-governance-pokayoke | MISSING_DOC |
| `hook:qa-commit-stage` | Pre-commit hook entrypoint. | precommit:qa-commit-stage:L44 | precommit:qa-commit-stage | MISSING_DOC |
| `hook:qa-push-stage` | Pre-commit hook entrypoint. | precommit:qa-push-stage:L66 | precommit:qa-push-stage | MISSING_DOC |
| `scripts/ci/apply_precommit_patch.sh` | Shell automation entrypoint. | filesystem_scan |  | MISSING_DOC |
| `scripts/ci/check_toolchain_parity.py` | Python automation entrypoint. | filesystem_scan<br>workflow:.github/workflows/quality-guardrails.yml:L115<br>workflow:.github/workflows/state-renorm-milestone-gate.yml:L92<br>workflow:.github/workflows/toolchain-parity-weekly.yml:L30 | workflow:quality-guardrails<br>workflow:state-renorm-milestone-gate<br>workflow:toolchain-parity-weekly | MISSING_DOC |
| `scripts/ci/run_stage_checks.py` | Python automation entrypoint. | filesystem_scan<br>make:qa-ci:L30<br>make:qa-commit:L24<br>make:qa-push:L27<br>precommit:qa-commit-stage:L44<br>precommit:qa-push-stage:L66<br>quality_stage:qa-commit:precommit_hook<br>quality_stage:qa-push:precommit_hook | make:qa-ci<br>make:qa-commit<br>make:qa-push<br>precommit:qa-commit-stage<br>precommit:qa-push-stage<br>quality_stage:qa-commit<br>quality_stage:qa-push | MISSING_DOC |
| `scripts/ci/scan_unused_code.py` | Python automation entrypoint. | filesystem_scan<br>quality_stage:qa-ci:commands[3] | quality_stage:qa-ci | MISSING_DOC |
| `scripts/ci/validate_5s_metrics.py` | Python automation entrypoint. | filesystem_scan<br>quality_stage:qa-ci:commands[2]<br>workflow:.github/workflows/quality-guardrails.yml:L34<br>workflow:.github/workflows/quality-guardrails.yml:L47 | quality_stage:qa-ci<br>workflow:quality-guardrails | MISSING_DOC |
| `scripts/ci/validate_5s_mission_traceability.py` | Python automation entrypoint. | filesystem_scan<br>quality_stage:qa-ci:commands[1] | quality_stage:qa-ci | MISSING_DOC |
| `scripts/dev/bootstrap_preflight.py` | Python automation entrypoint. | filesystem_scan<br>make:bootstrap-preflight:L4 | make:bootstrap-preflight | MISSING_DOC |
| `scripts/dev/verify_precommit_installed.py` | Python automation entrypoint. | filesystem_scan<br>make:verify-precommit-installed:L19 | make:verify-precommit-installed | MISSING_DOC |
