.PHONY: install run test lint format migrate revision up down

install:            ## Install the project with dev dependencies
	pip install -e ".[dev]"

run:                ## Run the API with autoreload
	uvicorn app.main:app --reload

test:               ## Run the test suite
	pytest

lint:               ## Check linting and formatting
	ruff check .
	black --check .

format:             ## Auto-fix lint issues and format
	ruff check . --fix
	black .

migrate:            ## Apply all pending migrations
	alembic upgrade head

revision:           ## Create a migration: make revision m="message"
	alembic revision -m "$(m)"

up:                 ## Start the full stack (Postgres + API) via Docker
	docker compose up --build

down:               ## Stop the stack
	docker compose down
