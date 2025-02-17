.PHONY: install test lint clean format check all pre-commit help

help:
	@echo "Available commands:"
	@echo "  make install      - Install project dependencies"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linting checks"
	@echo "  make format      - Format code with ruff"
	@echo "  make clean       - Remove Python compiled files and caches"
	@echo "  make check       - Run all checks (lint + test)"
	@echo "  make pre-commit  - Install pre-commit hooks"

install:
	poetry install

test:
	poetry run pytest

lint:
	poetry run ruff check .

format:
	poetry run ruff format .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +

check: lint test

pre-commit:
	poetry run pre-commit install

all: clean install pre-commit check
