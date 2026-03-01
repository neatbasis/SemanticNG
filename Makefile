.PHONY: bootstrap promotion-checks test test-cov

bootstrap:
	@python --version
	@python -m pip install --dry-run --no-build-isolation --no-deps -e ".[test]"
	@python -c "import pydantic; print(f'pydantic {pydantic.__version__}')"

promotion-checks:
	.github/scripts/run_promotion_checks.sh

test:
	pytest

test-cov:
	pytest --cov --cov-report=term-missing --cov-report=xml
