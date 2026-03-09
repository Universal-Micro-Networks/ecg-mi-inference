.PHONY: help build up down logs clean dev reset lint test

# Color output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)ECG MI Inference - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make dev              # Start development environment"
	@echo "  make build            # Build all Docker images"
	@echo "  make up               # Start all services"
	@echo "  make down             # Stop all services"
	@echo "  make logs             # View service logs"
	@echo "  make reset            # Reset database and start fresh"
	@echo "  make clean            # Remove all containers and volumes"

# Development commands
dev: ## Start development environment with hot reload
	@echo "$(BLUE)Starting development environment...$(NC)"
	docker-compose up --build

build: ## Build all Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build --no-cache

up: ## Start all services
	@echo "$(BLUE)Starting services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Services started!$(NC)"
	@echo "  Frontend: http://localhost:5173"
	@echo "  Backend:  http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose down

restart: ## Restart all services
	@echo "$(BLUE)Restarting services...$(NC)"
	docker-compose restart

# Logging and debugging
logs: ## View logs from all services (tail -f)
	docker-compose logs -f

logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

logs-backend: ## View backend logs
	docker-compose logs -f backend

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend sh

shell-backend: ## Open shell in backend container
	docker-compose exec backend bash

# Backend commands
backend-sync: ## Sync Python dependencies with uv
	@echo "$(BLUE)Syncing backend dependencies...$(NC)"
	cd backend && uv sync

backend-migration: ## Run database migrations (if needed)
	docker-compose exec backend python -m alembic upgrade head

backend-shell: ## Open Python shell in backend container
	docker-compose exec backend python

# Frontend commands
frontend-install: ## Install frontend dependencies
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	cd frontend && npm install

frontend-build: ## Build frontend for production
	@echo "$(BLUE)Building frontend...$(NC)"
	cd frontend && npm run build

# Database management
db-reset: ## Reset database and reinitialize with sample data
	@echo "$(YELLOW)Resetting database...$(NC)"
	rm -f backend/data/ecg_mi.db
	docker-compose restart backend
	@echo "$(GREEN)Database reset complete!$(NC)"

db-shell: ## Open SQLite shell
	sqlite3 backend/data/ecg_mi.db

# Testing and quality
test-backend: ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	docker-compose exec backend pytest tests/ -v

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	cd frontend && npm test

lint-backend: ## Lint backend code (flake8)
	@echo "$(BLUE)Linting backend code...$(NC)"
	docker-compose exec backend flake8 app/

lint-frontend: ## Lint frontend code (eslint)
	@echo "$(BLUE)Linting frontend code...$(NC)"
	cd frontend && npm run lint

format-backend: ## Format backend code (black)
	@echo "$(BLUE)Formatting backend code...$(NC)"
	docker-compose exec backend black app/

format-frontend: ## Format frontend code (prettier)
	@echo "$(BLUE)Formatting frontend code...$(NC)"
	cd frontend && npm run format

# Cleanup
clean: ## Remove all Docker containers, images, and volumes
	@echo "$(YELLOW)Removing Docker containers, images, and volumes...$(NC)"
	docker-compose down -v
	docker-compose rm -f
	@echo "$(GREEN)Cleanup complete!$(NC)"

clean-cache: ## Clean Docker build cache
	@echo "$(YELLOW)Cleaning Docker cache...$(NC)"
	docker builder prune -f

# Utilities
ps: ## Show running containers
	docker-compose ps

stats: ## Show container resource usage
	docker stats

status: ## Check service health status
	@echo "$(BLUE)Checking service health...$(NC)"
	@docker-compose ps
	@echo ""
	@echo "$(BLUE)Frontend health:$(NC)"
	@docker-compose exec frontend wget --quiet --spider http://localhost:5173 && echo "✓ Frontend is healthy" || echo "✗ Frontend is down"
	@echo "$(BLUE)Backend health:$(NC)"
	@docker-compose exec backend curl -s http://localhost:8000/health > /dev/null && echo "✓ Backend is healthy" || echo "✗ Backend is down"

# Development setup
setup: ## Initial setup - build images and start services
	@echo "$(BLUE)Setting up ECG MI Inference environment...$(NC)"
	make build
	make up
	@echo "$(GREEN)Setup complete! Access the application:$(NC)"
	@echo "  Frontend: http://localhost:5173"
	@echo "  Backend:  http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

reset: ## Reset everything and start fresh
	@echo "$(YELLOW)Performing full reset...$(NC)"
	make clean
	make build
	make up
	@echo "$(GREEN)Reset complete!$(NC)"

.DEFAULT_GOAL := help
