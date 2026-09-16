COMPOSE = docker compose --env-file .env -f infra/docker-compose.yml

.PHONY: initial-setup start-app stop-app logs check test lint build

initial-setup:
	@test -f .env || cp .env.template .env
	@./scripts/sync-version.sh
	@./scripts/generate-dev-certs.sh

start: initial-setup
	$(COMPOSE) up -d --build

stop:
	$(COMPOSE) stop

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

build:
	$(COMPOSE) build

check: test lint build
