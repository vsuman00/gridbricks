.PHONY: setup setup-backend setup-frontend backend-dev frontend-dev check check-backend check-frontend test-browser test-ui-runtime audit-security migrate ingest-fixtures ingest-sample ingest-january audit-january benchmark-api

setup: setup-backend setup-frontend

setup-backend:
	uv sync --project backend --locked --python 3.12

setup-frontend:
	npm --prefix frontend ci

backend-dev:
	backend/.venv/bin/python -m uvicorn gridbricks.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir backend/src

frontend-dev:
	npm --prefix frontend run dev

check: check-backend check-frontend

check-backend:
	backend/.venv/bin/ruff check --config backend/pyproject.toml backend scripts
	backend/.venv/bin/ruff format --check --config backend/pyproject.toml backend scripts
	backend/.venv/bin/python -m pytest backend/tests

check-frontend:
	npm --prefix frontend run lint
	npm --prefix frontend run typecheck
	npm --prefix frontend run test -- --run
	npm --prefix frontend run build

test-browser:
	npm --prefix frontend run test:browser

test-ui-runtime:
	backend/.venv/bin/python -m gridbricks.cli ingest-fixtures --data-dir data/fixtures > /dev/null
	npm --prefix frontend run build
	node frontend/scripts/verify-runtime.mjs

audit-security:
	uv audit --project backend --locked --python-version 3.12
	npm --prefix frontend audit

migrate:
	backend/.venv/bin/python -m gridbricks.cli migrate

ingest-fixtures:
	backend/.venv/bin/python -m gridbricks.cli ingest-fixtures --data-dir data/fixtures

ingest-sample:
	backend/.venv/bin/python -m gridbricks.cli ingest-sample

ingest-january:
	backend/.venv/bin/python -m gridbricks.cli ingest-january

audit-january:
	backend/.venv/bin/python -m gridbricks.cli audit-january

benchmark-api:
	backend/.venv/bin/python scripts/benchmark_api.py
