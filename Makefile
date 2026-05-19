.PHONY: help install install-sdk install-dev test test-cov lint lint-fix format typecheck security \
	docker-build docker-build-api docker-up docker-down docker-logs docker-clean \
	migrate worker celery flower redis-cli postgres-cli clean clean-all pre-commit ci release \
	health port-forward run-api run-mcp

PYTHON := python
PYTEST := python -m pytest
UV := uv

help: ## Show all targets with documentation
	@grep -E '^([a-zA-Z_-]+).*:.*## .*' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: install-sdk ## Install project and SDK dependencies
	$(UV) pip install -e ".[dev]"

install-sdk: ## Install the migrator_gen SDK package in editable mode
	$(UV) pip install -e "sdk/python[all]"

install-dev: install install-sdk ## Install everything with dev extras

test: ## Run tests
	$(PYTEST) tests/ -v

test-sdk: ## Run SDK tests
	$(PYTEST) sdk/python/tests/ -v

test-cov: ## Run tests with coverage report
	$(PYTEST) --cov=core --cov=migrator_gen --cov-report=html --cov-report=term tests/ sdk/python/tests/

lint: ## Run ruff linter
	ruff check sdk/python/core/ sdk/python/migrator_gen/ cli/ mcp/ backend/ shared/ tests/

lint-fix: ## Run ruff linter with auto-fix
	ruff check --fix sdk/python/core/ sdk/python/migrator_gen/ cli/ mcp/ backend/ shared/ tests/

format: ## Format code with ruff
	ruff format sdk/python/core/ sdk/python/migrator_gen/ cli/ mcp/ backend/ shared/ tests/

typecheck: ## Run mypy type checker
	mypy sdk/python/migrator_gen/ sdk/python/core/ cli/ mcp/ backend/ --ignore-missing-imports

security: ## Run security scans with Bandit
	bandit -r cli/ mcp/ backend/ -f screen

sdk-test: ## Run SDK's own test suite
	cd sdk/python && $(PYTEST) tests/ -v

sdk-lint: ## Lint SDK only
	ruff check sdk/python/core/ sdk/python/migrator_gen/ sdk/python/tests/

# ── Application runners ──────────────────────────────────────

run-api: ## Start the REST API server
	$(PYTHON) -m backend.api.src.server

run-mcp: ## Start the MCP server (stdio transport)
	$(PYTHON) -m mcp.server

# ── Docker ───────────────────────────────────────────────────

docker-build: ## Build Docker images
	docker build -t migrator-gen:latest -f infra/docker/Dockerfile .

docker-build-api: ## Build API Docker image
	docker build -f infra/docker/Dockerfile.api -t migrator-gen-api:latest .

docker-up: ## Start Docker Compose services
	docker compose -f infra/docker/docker-compose.yml up -d

docker-down: ## Stop Docker Compose services
	docker compose -f infra/docker/docker-compose.yml down

docker-logs: ## Follow Docker Compose logs
	docker compose -f infra/docker/docker-compose.yml logs -f

docker-clean: ## Clean up Docker resources
	docker compose -f infra/docker/docker-compose.yml down -v --rmi all

# ── Workers / Background ─────────────────────────────────────

migrate: ## Apply pending database migrations
	alembic upgrade head

worker: ## Run migration worker
	$(PYTHON) -m backend.worker.src.run

celery: ## Run Celery worker
	celery -A backend.worker.src.celery_app worker --loglevel=info

flower: ## Run Celery Flower monitoring
	celery -A backend.worker.src.celery_app flower --port=5555

redis-cli: ## Open Redis CLI
	docker compose -f infra/docker/docker-compose.yml exec redis redis-cli

postgres-cli: ## Open PostgreSQL CLI
	docker compose -f infra/docker/docker-compose.yml exec postgres psql -U migrator_user -d migrator_platform

# ── Housekeeping ─────────────────────────────────────────────

clean: ## Clean Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true

clean-all: clean ## Clean all build artifacts
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info generated/ .mypy_cache .ruff_cache

pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

ci: lint test security ## Run CI pipeline (lint, test, security)

release: ## Create and push git tag for release
	@read -p "Enter version (e.g., 0.2.0): " VERSION; \
	git tag v$$VERSION && git push --tags

health: ## Check API health endpoint
	curl -s http://localhost:8000/health

port-forward: ## Port forward to Kubernetes service
	kubectl port-forward svc/migration-api 8000:8000
