.PHONY: install format lint test run clean help db-init wireframe wireframe-down

# === Setup ===
install:
	uv sync --directory backend --dev
	@if git rev-parse --git-dir > /dev/null 2>&1; then \
		uv run --directory backend pre-commit install; \
	else \
		echo "⚠️  Not a git repository - skipping pre-commit install"; \
		echo "   Run 'git init && make install' to set up pre-commit hooks"; \
	fi
	@echo ""
	@echo "✅ Installation complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  • make docker-db        # Start PostgreSQL"
	@echo "  • make db-upgrade       # Apply migrations"
	@echo "  • make run              # Start development server"
	@echo ""
	@echo "Note: backend/.env is pre-configured for development"

# === Code Quality ===
format:
	uv run --directory backend ruff format app tests cli
	uv run --directory backend ruff check app tests cli --fix

lint:
	uv run --directory backend ruff check app tests cli
	uv run --directory backend ruff format app tests cli --check
	uv run --directory backend mypy app

# === Testing ===
test:
	uv run --directory backend pytest tests/ -v

test-cov:
	uv run --directory backend pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

# === Database ===
db-init: docker-db
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 3
	uv run --directory backend wireframe db upgrade
	@echo ""
	@echo "✅ Database initialized!"

db-migrate:
	@read -p "Migration message: " msg; \
	uv run --directory backend wireframe db migrate -m "$$msg"

db-upgrade:
	uv run --directory backend wireframe db upgrade

db-downgrade:
	uv run --directory backend wireframe db downgrade

db-current:
	uv run --directory backend wireframe db current

db-history:
	uv run --directory backend wireframe db history

# === Server ===
run:
	uv run --directory backend wireframe server run --reload

run-prod:
	uv run --directory backend wireframe server run --host 0.0.0.0 --port 8000

routes:
	uv run --directory backend wireframe server routes

# === Users ===
create-admin:
	@echo "Creating admin user..."
	uv run --directory backend wireframe user create-admin

user-create:
	uv run --directory backend wireframe user create

user-list:
	uv run --directory backend wireframe user list

# === Taskiq ===
taskiq-worker:
	uv run --directory backend wireframe taskiq worker

taskiq-scheduler:
	uv run --directory backend wireframe taskiq scheduler

# === Docker: Development (Full Stack) ===
wireframe:
	docker-compose -f docker-compose.dev.yml up -d
	@echo ""
	@echo "✅ Development environment started!"
	@echo ""
	@echo "   Frontend:    http://localhost:3000"
	@echo "   Backend API: http://localhost:8000"
	@echo "   API Docs:    http://localhost:8000/docs"
	@echo "   Admin Panel: http://localhost:8000/admin"
	@echo "   PostgreSQL:  localhost:5432"
	@echo "   Redis:       localhost:6379"
	@echo ""
	@echo "   Logs: make wireframe-logs"
	@echo "   Stop: make wireframe-down"

wireframe-down:
	docker-compose -f docker-compose.dev.yml down

wireframe-logs:
	docker-compose -f docker-compose.dev.yml logs -f

wireframe-build:
	docker-compose -f docker-compose.dev.yml build

wireframe-shell:
	docker-compose -f docker-compose.dev.yml exec backend /bin/bash

# === Docker: Production (with Traefik) ===
docker-prod:
	docker-compose -f docker-compose.prod.yml up -d
	@echo ""
	@echo "✅ Production services started with Traefik!"
	@echo ""
	@echo "Endpoints (replace DOMAIN with your domain):"
	@echo "   Frontend: https://$$DOMAIN"
	@echo "   API: https://api.$$DOMAIN"
	@echo "   Traefik: https://traefik.$$DOMAIN"

docker-prod-down:
	docker-compose -f docker-compose.prod.yml down

docker-prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f

docker-prod-build:
	docker-compose -f docker-compose.prod.yml build

# === Docker: Individual Services (Dev) ===
docker-db:
	docker-compose -f docker-compose.dev.yml up -d db
	@echo ""
	@echo "✅ PostgreSQL started on port 5432"
	@echo "   Connection: postgresql://postgres:postgres@localhost:5432/wireframe"

docker-db-stop:
	docker-compose -f docker-compose.dev.yml stop db

docker-redis:
	docker-compose -f docker-compose.dev.yml up -d redis
	@echo ""
	@echo "✅ Redis started on port 6379"

docker-redis-stop:
	docker-compose -f docker-compose.dev.yml stop redis

# === Cleanup ===
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml

# === Help ===
help:
	@echo ""
	@echo "wireframe - Available Commands"
	@echo "======================================"
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install dependencies + pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  make run           Start dev server (with hot reload)"
	@echo "  make test          Run tests"
	@echo "  make lint          Check code quality"
	@echo "  make format        Auto-format code"
	@echo ""
	@echo "Database:"
	@echo "  make db-init       Initialize database (start + migrate)"
	@echo "  make db-migrate    Create new migration"
	@echo "  make db-upgrade    Apply migrations"
	@echo "  make db-downgrade  Rollback last migration"
	@echo "  make db-current    Show current migration"
	@echo ""
	@echo "Users:"
	@echo "  make create-admin  Create admin user (for SQLAdmin access)"
	@echo "  make user-create   Create new user (interactive)"
	@echo "  make user-list     List all users"
	@echo ""
	@echo "Taskiq:"
	@echo "  make taskiq-worker     Start Taskiq worker"
	@echo "  make taskiq-scheduler  Start Taskiq scheduler"
	@echo ""
	@echo "Docker (Development):"
	@echo "  make wireframe            Start full dev stack (backend, frontend, db, redis)"
	@echo "  make wireframe-down       Stop dev stack"
	@echo "  make wireframe-logs       View dev logs"
	@echo "  make wireframe-build      Build dev images"
	@echo "  make wireframe-shell      Shell into backend container"
	@echo "  make docker-db            Start only PostgreSQL"
	@echo "  make docker-redis         Start only Redis"
	@echo ""
	@echo "Docker (Production with Traefik):"
	@echo "  make docker-prod          Start production stack"
	@echo "  make docker-prod-down     Stop production stack"
	@echo "  make docker-prod-logs     View production logs"
	@echo "  make docker-prod-build    Build production images"
	@echo ""
	@echo "Other:"
	@echo "  make routes        Show all API routes"
	@echo "  make clean         Clean cache files"
	@echo ""
