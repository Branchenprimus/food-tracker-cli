.PHONY: deploy down logs dev master

dev:
	docker compose -f deploy/compose.yml down
	docker compose build --build-arg APP_VERSION=$$(git describe --tags --always --dirty) --build-arg APP_ENV=dev
	docker compose up -d

master:
	docker compose down
	docker compose -f deploy/compose.yml pull && docker compose -f deploy/compose.yml up -d

deploy:
	docker compose -f deploy/compose.yml up -d

down:
	docker compose down
	docker compose -f deploy/compose.yml down

logs:
	docker compose logs -f || docker compose -f deploy/compose.yml logs -f
