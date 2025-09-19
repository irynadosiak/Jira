.PHONY: help install migrate runserver test lint format check-format type-check clean

help:
	@echo "Simple Task Manager Commands:"
	@echo "  install       - Install dependencies"
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
	pip3 install -r requirements.txt

migrate:
	python3 manage.py makemigrations
	python3 manage.py migrate

runserver:
	python3 manage.py runserver

test:
	python3 manage.py test

# Linting commands
lint: check-format type-check
	@echo "Running flake8..."
	flake8 .
	@echo "Checking import order..."
	isort --check-only --diff .
	@echo "✅ All linting checks passed!"

format:
	@echo "Formatting with black..."
	black .
	@echo "Sorting imports with isort..."
	isort .
	@echo "✅ Code formatted!"

check-format:
	@echo "Checking code formatting..."
	black --check .

type-check:
	@echo "Running mypy type checking..."
	mypy .

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	@echo "✅ Cache files cleaned!"
