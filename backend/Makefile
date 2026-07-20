# ==============================================
# AI QA Platform - Backend Makefile
# ==============================================
# Usage: make <target>
# ==============================================

.PHONY: help install dev run test lint format migrate docker clean

# Default target
.DEFAULT_GOAL := help

# Python executable
PYTHON := python3
PIP := pip3

# Application
APP_MODULE := app.main:app
HOST := 0.0.0.0
PORT := 8000

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# ---------------------------------------------
# Help
# ---------------------------------------------
help: ## Show this help message
	@echo "$(BLUE)AI QA Platform - Backend Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Usage:$(NC) make $(YELLOW)<target>$(NC)"
	@echo ""
	@echo "$(GREEN)Targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'

# ---------------------------------------------
# Installation
# ---------------------------------------------
install: ## Install production dependencies
	$(PIP) install -r requirements.txt

dev: ## Install all dependencies (production + development)
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)Development dependencies installed$(NC)"

venv: ## Create virtual environment
	$(PYTHON) -m venv venv
	@echo "$(GREEN)Virtual environment created. Activate with: source venv/bin/activate$(NC)"

# ---------------------------------------------
# Running
# ---------------------------------------------
run: ## Run the application (development mode with reload)
	uvicorn $(APP_MODULE) --host $(HOST) --port $(PORT) --reload

run-prod: ## Run the application (production mode)
	uvicorn $(APP_MODULE) --host $(HOST) --port $(PORT) --workers 4

# ---------------------------------------------
# Database & Migrations
# ---------------------------------------------
migrate: ## Run database migrations
	alembic upgrade head
	@echo "$(GREEN)Migrations applied$(NC)"

migrate-down: ## Rollback last migration
	alembic downgrade -1
	@echo "$(YELLOW)Rolled back one migration$(NC)"

migrate-create: ## Create new migration (usage: make migrate-create msg="description")
	@if [ -z "$(msg)" ]; then \
		echo "$(RED)Error: Please provide a migration message$(NC)"; \
		echo "Usage: make migrate-create msg=\"your migration description\""; \
		exit 1; \
	fi
	alembic revision --autogenerate -m "$(msg)"
	@echo "$(GREEN)Migration created$(NC)"

migrate-history: ## Show migration history
	alembic history

migrate-current: ## Show current migration revision
	alembic current

db-init: ## Initialize database (run migrations)
	alembic upgrade head
	@echo "$(GREEN)Database initialized$(NC)"

# ---------------------------------------------
# Testing
# ---------------------------------------------
test: ## Run all tests
	pytest tests/ -v

test-cov: ## Run tests with coverage report
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)Coverage report generated in htmlcov/$(NC)"

test-fast: ## Run tests without coverage (faster)
	pytest tests/ -v -x --tb=short

# ---------------------------------------------
# Code Quality
# ---------------------------------------------
lint: ## Run linting checks
	flake8 app/ tests/
	mypy app/
	@echo "$(GREEN)Linting passed$(NC)"

format: ## Format code with black and isort
	black app/ tests/
	isort app/ tests/
	@echo "$(GREEN)Code formatted$(NC)"

format-check: ## Check code formatting without changes
	black --check app/ tests/
	isort --check-only app/ tests/

# ---------------------------------------------
# Docker
# ---------------------------------------------
docker-build: ## Build Docker image
	docker build -t ai-qa-backend:latest .
	@echo "$(GREEN)Docker image built$(NC)"

docker-run: ## Run Docker container
	docker run -p 8000:8000 --env-file .env ai-qa-backend:latest

docker-shell: ## Open shell in Docker container
	docker run -it --rm ai-qa-backend:latest /bin/bash

# ---------------------------------------------
# Cleanup
# ---------------------------------------------
clean: ## Remove generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "$(GREEN)Cleaned up generated files$(NC)"

clean-all: clean ## Remove all generated files including venv
	rm -rf venv/
	@echo "$(GREEN)Cleaned up everything including virtual environment$(NC)"

# ---------------------------------------------
# Utility
# ---------------------------------------------
shell: ## Open Python shell with app context
	$(PYTHON) -c "from app.main import app; import code; code.interact(local=dict(app=app))"

routes: ## List all registered routes
	$(PYTHON) -c "from app.main import app; [print(f'{r.methods} {r.path}') for r in app.routes]"

check: format lint test ## Run all checks (format, lint, test)
	@echo "$(GREEN)All checks passed!$(NC)"
