.PHONY: bootstrap qa-hook-parity qa-local promotion-checks test test-cov

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

qa-local: bootstrap qa-hook-parity
	pytest --cov --cov-report=term-missing --cov-report=xml
	mypy --config-file=pyproject.toml src tests

promotion-checks:
	.github/scripts/run_promotion_checks.sh

test:
	pytest

test-cov:
	pytest --cov --cov-report=term-missing --cov-report=xml
