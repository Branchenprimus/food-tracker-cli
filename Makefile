.PHONY: deploy dev down down-dev down-deploy logs logs-dev logs-deploy

DEPLOY_COMPOSE = docker compose --env-file .env -f deploy/compose.yml
DEV_COMPOSE = docker compose -f docker-compose.yml
DEPLOY_URL = http://localhost:8787
DEV_URL = http://localhost:8686
APP_VERSION = $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)
APP_COMMIT = $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)

deploy:
	$(DEPLOY_COMPOSE) pull
	$(DEPLOY_COMPOSE) up -d
	@echo "Deploy instance available at:"
	@echo "$(DEPLOY_URL)"

dev:
	$(DEV_COMPOSE) build --build-arg APP_VERSION=$(APP_VERSION) --build-arg APP_COMMIT=$(APP_COMMIT) --build-arg APP_ENV=dev
	$(DEV_COMPOSE) up -d
	@echo "Dev instance available at:"
	@echo "$(DEV_URL)"

down: down-dev

down-dev:
	$(DEV_COMPOSE) down

down-deploy:
	$(DEPLOY_COMPOSE) down

logs: logs-dev

logs-dev:
	$(DEV_COMPOSE) logs -f

logs-deploy:
	$(DEPLOY_COMPOSE) logs -f
