.PHONY: help install install-dev test test-cov test-async lint format typecheck clean build publish

PYTHON := python
PYTEST := python -m pytest

help:
	@grep -E '^([a-zA-Z_-]+).*:.*## .*' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install SDK in editable mode with all extras
	$(PYTHON) -m pip install -e ".[all,dev]"

install-dev: ## Install SDK with all extras and dev dependencies
	$(PYTHON) -m pip install -e ".[all,dev]"
	$(PYTHON) -m pre-commit install

test: ## Run all SDK tests
	$(PYTEST) tests/ -v

test-cov: ## Run SDK tests with coverage report
	$(PYTEST) --cov=migrator_gen --cov-report=term --cov-report=html tests/

test-async: ## Run only async client tests
	$(PYTEST) tests/ -v -k "async"

lint: ## Run ruff linter
	ruff check src/migrator_gen/ tests/

format: ## Format code with ruff
	ruff format src/migrator_gen/ tests/

typecheck: ## Run mypy static type checking
	mypy src/migrator_gen/

clean: ## Clean Python cache and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf dist/ build/ .coverage htmlcov/

build: clean ## Build wheel and sdist
	$(PYTHON) -m build

publish: build ## Publish to PyPI
	$(PYTHON) -m twine upload dist/*
