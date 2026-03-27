.PHONY: install test format lint build publish clean all

# Değişkenler
PYTHON = python3
VENV_BIN = venv/bin

install:
	$(PYTHON) -m venv venv
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -e .[dev]
	$(VENV_BIN)/pip install build twine

test:
	$(VENV_BIN)/pytest

format:
	$(VENV_BIN)/black src tests

lint:
	$(VENV_BIN)/flake8 src tests
	$(VENV_BIN)/mypy src

build: clean
	$(VENV_BIN)/python -m build

publish: build
	$(VENV_BIN)/twine upload dist/*

clean:
	rm -rf dist/
	rm -rf build/
	rm -rf src/*.egg-info
	rm -rf htmlcov/
	rm -f .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

all: format lint test build
