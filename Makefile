.PHONY: deploy down logs dev

dev:
	docker compose up -d --build

deploy:
	docker compose -f deploy/compose.yml up -d

down:
	docker compose -f deploy/compose.yml down

logs:
	docker compose -f deploy/compose.yml logs -f
