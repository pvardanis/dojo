# ABOUTME: Dojo dev workflow. `make check` is the CI contract.
# ABOUTME: Spec §8.1 9 targets + test-flakes (SC #4 gate) + clean.

.PHONY: install format lint typecheck docstrings docparams test check \
        run migrate test-flakes clean

install:
	uv sync
	uv run pre-commit install

format:
	uv run ruff format .

lint:
	uv run ruff check .
	uv run lint-imports

typecheck:
	uv run ty check app

docstrings:
	uv run interrogate -c pyproject.toml app

docparams:
	uv run pydoclint --config=pyproject.toml app

test:
	uv run pytest

check: format lint typecheck docstrings docparams test

run:
	uv run uvicorn app.main:app --reload --port 8000

migrate:
	uv run alembic upgrade head

test-flakes:
	uv run pytest tests/integration/test_db_smoke.py --count=10

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
	rm -f dojo.db dojo.db-wal dojo.db-shm dojo.db-journal
