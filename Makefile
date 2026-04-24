# ABOUTME: Dojo dev workflow. `make check` is the CI contract.
# ABOUTME: Spec §8.1 9 targets + test-flakes (SC #4 gate) + clean.

.PHONY: install format lint typecheck docstrings docparams test check \
        run migrate test-flakes clean

install:
	uv sync
	# anthropic pulls in upstream `docstring-parser`; pydoclint pulls in
	# `docstring-parser-fork`. Both write to the same `docstring_parser/`
	# namespace and clobber non-deterministically on fresh `uv sync`. The
	# fork is a strict superset (adds `DocstringYields`), so we force it
	# to win by reinstalling after sync. Idempotent + cheap (single wheel).
	uv pip install --force-reinstall --no-deps docstring-parser-fork==0.0.14
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
