.PHONY: bootstrap qa-hook-parity qa-local-fast qa-full-type-surface qa-test-cov qa-ci-equivalent qa-local promotion-governance-check promotion-check promotion-checks scratch-hygiene test test-cov

bootstrap:
	@python --version
	@python -m pip --version
	@python -c "import importlib.util, pathlib, semanticng; assert importlib.util.find_spec('semanticng') is not None; package_path = pathlib.Path(semanticng.__file__).resolve(); print(f'semanticng import path: {package_path}')"
	@python -c "import pydantic; print(f'pydantic {pydantic.__version__}')"
	@python .github/scripts/print_env_provenance.py

qa-hook-parity:
	python .github/scripts/check_python_support_policy.py
	python .github/scripts/check_precommit_parity.py
	pre-commit run --all-files

qa-local-fast: qa-hook-parity

qa-test-cov:
	pytest --cov --cov-report=term-missing --cov-report=xml

qa-full-type-surface:
	mypy --config-file=pyproject.toml src tests

qa-ci-equivalent:
	python .github/scripts/check_no_regression_budget.py
	$(MAKE) qa-hook-parity
	$(MAKE) qa-test-cov
	$(MAKE) qa-full-type-surface

qa-local: bootstrap qa-hook-parity qa-test-cov qa-full-type-surface

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
