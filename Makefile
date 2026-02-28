.PHONY: promotion-checks test test-cov

promotion-checks:
	.github/scripts/run_promotion_checks.sh

test:
	pytest

test-cov:
	pytest --cov --cov-report=term-missing --cov-report=xml
