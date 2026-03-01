.PHONY: bootstrap promotion-checks test test-cov

bootstrap:
	@python --version
	@python -c "import pydantic; print(f'pydantic {pydantic.__version__}')"

promotion-checks:
	.github/scripts/run_promotion_checks.sh

test:
	pytest

test-cov:
	pytest --cov --cov-report=term-missing --cov-report=xml
