.PHONY: help build build-ssh up down logs clean dev dev-ssh reset lint test db-clear-clinical vendor-mfer-tools vendor-inference-bnp specs-pdf

# Compose v2 推奨（build.ssh は v2 系）。未インストールなら Docker Desktop の CLI を確認してください。
DOCKER_COMPOSE ?= docker compose

# Docker 用: 非公開 mfer-tools をホストで取得（コミット対象外）
MFER_TOOLS_GIT_URL ?= https://github.com/tkwataru/mfer-tools.git
MFER_TOOLS_COMMIT ?= main

# BNP 推論（inference_ecg_bnp）。非公開時は gh auth login 済みの HTTPS または SSH URLを指定
INFERENCE_ECG_BNP_GIT_URL ?= https://github.com/tkwataru/inference_ecg_bnp.git
INFERENCE_ECG_BNP_COMMIT ?= main
PANDOC_IMAGE ?= pandoc/latex:latest
PANDOC_PLATFORM ?= linux/amd64

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
	@echo "  make dev-ssh          # dev と同様 + バックエンド mfer-tools を SSH でビルド"

vendor-mfer-tools: ## Clone mfer-tools into backend/vendor (needed before docker build; use SSH URL if private)
	@if [ -f backend/vendor/mfer-tools/pyproject.toml ]; then \
		echo "$(GREEN)mfer-tools は既に backend/vendor/mfer-tools にあります$(NC)"; \
	else \
		rm -rf backend/vendor/mfer-tools && \
		mkdir -p backend/vendor && \
		git clone "$(MFER_TOOLS_GIT_URL)" backend/vendor/mfer-tools && \
		git -C backend/vendor/mfer-tools checkout "$(MFER_TOOLS_COMMIT)" && \
		echo "$(GREEN)backend/vendor/mfer-tools を取得しました（commit $(MFER_TOOLS_COMMIT)）$(NC)"; \
	fi

vendor-inference-bnp: ## vendor に inference_ecg_bnp を clone（Git 依存が使えないオフライン等のフォールバック）
	@if [ -f backend/vendor/inference_ecg_bnp/pyproject.toml ]; then \
		echo "$(GREEN)inference_ecg_bnp は既に backend/vendor/inference_ecg_bnp にあります$(NC)"; \
	else \
		rm -rf backend/vendor/inference_ecg_bnp && \
		mkdir -p backend/vendor && \
		git clone "$(INFERENCE_ECG_BNP_GIT_URL)" backend/vendor/inference_ecg_bnp && \
		git -C backend/vendor/inference_ecg_bnp checkout "$(INFERENCE_ECG_BNP_COMMIT)" && \
		touch backend/vendor/inference_ecg_bnp/.gitkeep && \
		echo "$(GREEN)backend/vendor/inference_ecg_bnp を取得しました（commit $(INFERENCE_ECG_BNP_COMMIT)）$(NC)"; \
	fi

# Development commands
dev: ## Start development environment with hot reload
	@test -f backend/vendor/mfer-tools/pyproject.toml || ( \
		echo "$(YELLOW)Docker ビルドに必要: make vendor-mfer-tools$(NC)"; \
		exit 1; \
	)
	@test -f backend/vendor/inference_ecg_bnp/pyproject.toml || ( \
		echo "$(YELLOW)Docker ビルドに必要: make vendor-inference-bnp$(NC)"; \
		exit 1; \
	)
	@echo "$(BLUE)Starting development environment...$(NC)"
	docker-compose up --build

dev-ssh: ## dev と同様（旧: mfer SSH ビルド。バックエンドは uv.lock の git 依存を使用）
	DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 $(DOCKER_COMPOSE) \
		-f docker-compose.yml -f docker-compose.ssh.yml build --ssh default && \
	DOCKER_BUILDKIT=1 $(DOCKER_COMPOSE) \
		-f docker-compose.yml -f docker-compose.ssh.yml up

build: ## Build all Docker images
	@test -f backend/vendor/mfer-tools/pyproject.toml || ( \
		echo "$(YELLOW)Docker ビルドに必要: make vendor-mfer-tools$(NC)"; \
		exit 1; \
	)
	@test -f backend/vendor/inference_ecg_bnp/pyproject.toml || ( \
		echo "$(YELLOW)Docker ビルドに必要: make vendor-inference-bnp$(NC)"; \
		exit 1; \
	)
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build --no-cache

build-ssh: ## Build images（旧: mfer SSH。バックエンドは uv.lock の HTTPS git をビルド時に取得）
	@echo "$(BLUE)Building Docker images (backend mfer-tools via SSH)...$(NC)"
	DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 $(DOCKER_COMPOSE) \
		-f docker-compose.yml -f docker-compose.ssh.yml build --ssh default --no-cache

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

# 診断=inferences、診察=examinations、患者=patients（system_config / token_blacklist は残す）
db-clear-clinical: ## Delete all patient, examination, and inference records from SQLite
	@if [ ! -f backend/data/ecg_mi.db ]; then \
		echo "$(YELLOW)No database at backend/data/ecg_mi.db — nothing to do.$(NC)"; \
		exit 0; \
	fi
	@echo "$(YELLOW)Deleting inferences, examinations, and patients...$(NC)"
	sqlite3 backend/data/ecg_mi.db "PRAGMA foreign_keys = ON; \
		DELETE FROM inferences; \
		DELETE FROM examinations; \
		DELETE FROM patients; \
		VACUUM;"
	@echo "$(BLUE)Restarting backend to clear in-memory folder-watcher tracked cache...$(NC)"
	docker-compose restart backend
	@echo "$(GREEN)Clinical records cleared (patients, examinations, inferences).$(NC)"

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

specs-pdf: ## Convert all Markdown under .kiro/specs to PDF
	@echo "$(BLUE)Converting spec Markdown files to PDF...$(NC)"
	@mkdir -p .kiro/specs-pdf
	@files="$$(python3 -c 'import pathlib; [print(str(p)) for p in sorted(pathlib.Path(".kiro/specs").rglob("*.md"))]')"; \
	if [ -z "$$files" ]; then \
		echo "$(YELLOW)No markdown files found under .kiro/specs.$(NC)"; \
		exit 0; \
	fi; \
	for f in $$files; do \
		rel="$${f#.kiro/specs/}"; \
		out=".kiro/specs-pdf/$${rel%.md}.pdf"; \
		mkdir -p "$$(dirname "$$out")"; \
		echo "$(BLUE) -> $$f$(NC)"; \
		docker run --rm \
			--platform "$(PANDOC_PLATFORM)" \
			-v "$$(pwd):/work" \
			-w /work \
			"$(PANDOC_IMAGE)" \
			"$$f" \
			-o "$$out" \
			--pdf-engine=xelatex; \
	done
	@echo "$(GREEN)PDF export complete: .kiro/specs-pdf$(NC)"

.DEFAULT_GOAL := help
