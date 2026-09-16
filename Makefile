COMPOSE = docker compose --env-file .env -f infra/docker-compose.yml

.PHONY: initial-setup start-app stop-app logs

initial-setup:
	@test -f .env || cp .env.template .env
	@./scripts/sync-version.sh
	@./scripts/generate-dev-certs.sh

start: initial-setup
	$(COMPOSE) up -d --build

stop:
	$(COMPOSE) stop

logs:
	$(COMPOSE) logs -f
