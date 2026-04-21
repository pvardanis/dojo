# ABOUTME: Dojo dev workflow. `make check` is the CI contract.
# ABOUTME: Spec §8.1 9 targets + test-flakes (SC #4 gate).

.PHONY: install format lint typecheck docstrings test check run \
        migrate test-flakes

install:
	uv sync
	uv run pre-commit install

format:
	uv run ruff format .

lint:
	uv run ruff check --fix .

typecheck:
	uv run ty check app

docstrings:
	uv run interrogate -c pyproject.toml app

test:
	uv run pytest

check: format lint typecheck docstrings test

run:
	uv run uvicorn app.main:app --reload --port 8000

migrate:
	uv run alembic upgrade head

test-flakes:
	uv run pytest tests/integration/test_db_smoke.py --count=10
