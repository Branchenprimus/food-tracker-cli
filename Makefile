.PHONY: deploy down logs

deploy:
	docker compose -f deploy/compose.yml up -d

down:
	docker compose -f deploy/compose.yml down

logs:
	docker compose -f deploy/compose.yml logs -f
