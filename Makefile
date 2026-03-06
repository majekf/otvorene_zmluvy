.PHONY: help install dev start test test-backend test-frontend lint build docker clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies (Python + Node)
	pip install -r requirements.txt
	cd frontend && npm ci

dev: ## Start backend + frontend dev servers
	@echo "Starting GovLens development servers..."
	@echo "Backend:  http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload &
	@cd frontend && npm run dev

start: ## Start production backend server
	python -m uvicorn src.api:app --host 0.0.0.0 --port 8000

test: test-backend test-frontend ## Run all tests

test-backend: ## Run Python backend tests
	pytest tests/ -v

test-frontend: ## Run frontend vitest tests
	cd frontend && npx vitest run

lint: ## Lint frontend code
	cd frontend && npm run lint

build: ## Build frontend for production
	cd frontend && npm run build

docker: ## Build and start with Docker Compose
	docker compose up --build

docker-down: ## Stop Docker Compose services
	docker compose down

clean: ## Remove build artifacts
	rm -rf frontend/dist frontend/node_modules/.vite
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
