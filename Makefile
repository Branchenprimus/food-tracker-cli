.PHONY: deploy down logs dev master

dev:
	docker compose -f deploy/compose.yml down
	docker compose up -d --build

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
