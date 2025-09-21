.PHONY: help install migrate runserver test lint format check-format type-check clean

help:
	@echo "Simple Task Manager Commands:"
	@echo "  install       - Install dependencies with Poetry"
	@echo "  migrate       - Set up database"
	@echo "  runserver     - Start development server"
	@echo "  test          - Run tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint          - Run all linters (flake8, mypy, isort check)"
	@echo "  format        - Format code with black and isort"
	@echo "  check-format  - Check if code is formatted correctly"
	@echo "  type-check    - Run mypy type checking"
	@echo ""
	@echo "  clean         - Remove cache files"

install:
	poetry install

migrate:
	poetry run python manage.py makemigrations
	poetry run python manage.py migrate

runserver:
	poetry run python manage.py runserver

test:
	poetry run python manage.py test

# Linting commands
lint: check-format type-check
	@echo "Running flake8..."
	poetry run flake8 . --exclude="venv,.venv,__pycache__,.git,*/migrations/*"
	@echo "Checking import order..."
	poetry run isort --check-only --diff .
	@echo "✅ All linting checks passed!"

format:
	@echo "Formatting with black..."
	poetry run black .
	@echo "Sorting imports with isort..."
	poetry run isort .
	@echo "✅ Code formatted!"

check-format:
	@echo "Checking code formatting..."
	poetry run black --check .

type-check:
	@echo "Running mypy type checking..."
	poetry run mypy .

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	@echo "✅ Cache files cleaned!"
