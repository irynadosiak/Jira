.PHONY: help install migrate runserver test

help:
	@echo "Simple Task Manager Commands:"
	@echo "  install    - Install dependencies"
	@echo "  migrate    - Set up database"
	@echo "  runserver  - Start development server"
	@echo "  test       - Run tests"

install:
	pip3 install -r requirements.txt

migrate:
	python3 manage.py makemigrations
	python3 manage.py migrate

runserver:
	python3 manage.py runserver

test:
	python3 manage.py test