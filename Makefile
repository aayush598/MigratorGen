.PHONY: help install install-dev test test-cov lint lint-fix format typecheck security \
	docker-build docker-build-api docker-up docker-down docker-logs docker-clean \
	migrate worker celery flower redis-cli postgres-cli clean clean-all pre-commit ci release \
	health port-forward

PYTHON := python
PYTEST := python -m pytest
UV := uv

help: ## Show all targets with documentation
	@grep -E '^([a-zA-Z_-]+).*:.*## .*' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	$(UV) pip install -e .

install-dev: ## Install dependencies with dev tools
	$(UV) pip install -e ".[dev]"

test: ## Run tests
	$(PYTEST) tests/ -v

test-cov: ## Run tests with coverage report
	$(PYTEST) --cov=core --cov-report=html --cov-report=term tests/

lint: ## Run ruff linter
	ruff check .

lint-fix: ## Run ruff linter with auto-fix
	ruff check --fix .

format: ## Format code with ruff
	ruff format .

typecheck: ## Run mypy type checker
	mypy core/ api/ mcp/ tests/ --ignore-missing-imports

security: ## Run security scans with Bandit
	bandit -r core/ api/ mcp/ -f screen

docker-build: ## Build Docker images
	docker build -t migratorgen:latest .

docker-build-api: ## Build API Docker image
	docker build -f Dockerfile.api -t migratorgen-api:latest .

docker-up: ## Start Docker Compose services
	docker compose up -d

docker-down: ## Stop Docker Compose services
	docker compose down

docker-logs: ## Follow Docker Compose logs
	docker compose logs -f

docker-clean: ## Clean up Docker resources
	docker compose down -v --rmi all

migrate: ## Apply pending database migrations
	alembic upgrade head

worker: ## Run migration worker
	$(PYTHON) -m services.worker.run

celery: ## Run Celery worker
	celery -A services.tasks.celery_app worker --loglevel=info

flower: ## Run Celery Flower monitoring
	celery -A services.tasks.celery_app flower --port=5555

redis-cli: ## Open Redis CLI
	docker compose exec redis redis-cli

postgres-cli: ## Open PostgreSQL CLI
	docker compose exec postgres psql -U migrator_user -d migrator_platform

clean: ## Clean Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true

clean-all: ## Clean all build artifacts
	$(MAKE) clean
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info

pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

ci: ## Run CI pipeline (lint, test, security)
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) security

release: ## Create and push git tag for release
	@read -p "Enter version (e.g., 0.2.0): " VERSION; \
	git tag v$$VERSION && git push --tags

health: ## Check API health endpoint
	curl -s http://localhost:8000/health

port-forward: ## Port forward to Kubernetes service
	kubectl port-forward svc/migration-api 8000:8000
