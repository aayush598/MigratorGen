.PHONY: install install-dev test lint format typecheck clean

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v --tb=short

test-cov:
	python -m pytest tests/ --cov=cli --cov-report=term-missing

lint:
	python -m ruff check src/

format:
	python -m ruff format src/ tests/

typecheck:
	python -m mypy src/

clean:
	rm -rf .pytest_cache __pycache__
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
