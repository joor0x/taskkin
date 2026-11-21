.PHONY: up down build migrate seed test lint format logs shell

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m app.db.seed

test:
	docker compose exec backend pytest --cov=app --cov-report=term-missing tests/

lint:
	docker compose exec backend ruff check .
	docker compose exec backend mypy app

format:
	docker compose exec backend ruff format .

logs:
	docker compose logs -f

shell:
	docker compose exec backend bash
