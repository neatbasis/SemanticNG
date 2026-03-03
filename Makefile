.PHONY: bootstrap-preflight setup-dev bootstrap verify-precommit-installed verify-dev-setup qa-commit qa-push qa-ci qa-baseline qa-hook-parity qa-hook-parity-diagnostics qa-local-fast qa-full-type qa-full-type-surface qa-test-cov qa-ci-equivalent qa-local promotion-governance-check promotion-check promotion-checks scratch-hygiene status status-json status-check status-sync-check program-sync test test-cov

bootstrap-preflight:
	python scripts/dev/bootstrap_preflight.py

setup-dev: bootstrap-preflight
	pre-commit install --hook-type pre-commit --hook-type pre-push
	pre-commit install-hooks
	$(MAKE) verify-precommit-installed
	@python --version
	@python -m pip --version
	@python -c "import importlib.util, pathlib, semanticng; assert importlib.util.find_spec('semanticng') is not None; package_path = pathlib.Path(semanticng.__file__).resolve(); print(f'semanticng import path: {package_path}')"
	@python -c "import pydantic; print(f'pydantic {pydantic.__version__}')"
	@python .github/scripts/print_env_provenance.py

bootstrap: setup-dev

verify-precommit-installed:
	python scripts/dev/verify_precommit_installed.py

verify-dev-setup: bootstrap-preflight verify-precommit-installed

qa-commit:
	python scripts/ci/run_stage_checks.py qa-commit

qa-push:
	python scripts/ci/run_stage_checks.py qa-push

qa-ci:
	python scripts/ci/run_stage_checks.py qa-ci


qa-baseline:
	$(MAKE) qa-push

qa-hook-parity:
	python .github/scripts/check_python_support_policy.py
	python .github/scripts/check_precommit_parity.py
	pre-commit run --all-files

qa-hook-parity-diagnostics:
	python .github/scripts/run_hook_parity_with_diagnostics.py

qa-local-fast: qa-commit

qa-test-cov:
	pytest --cov --cov-report=term-missing --cov-report=xml

qa-full-type:
	$(MAKE) qa-full-type-surface

qa-full-type-surface:
	mypy --config-file=pyproject.toml src tests

qa-ci-equivalent:
	$(MAKE) qa-ci

qa-local: verify-dev-setup qa-push qa-test-cov qa-full-type-surface

scratch-hygiene:
	python .github/scripts/check_root_scratch_files.py

promotion-governance-check:
	.github/scripts/run_promotion_checks.sh

promotion-check: promotion-governance-check

promotion-checks: promotion-governance-check

test:
	pytest

test-cov:
	$(MAKE) qa-test-cov


status:
	python scripts/dev/status_report.py status

status-json:
	python scripts/dev/status_report.py status-json

status-check:
	python scripts/dev/status_report.py status-check

program-sync:
	python scripts/ci/validate_program_sync.py

status-sync-check: program-sync
