.PHONY: help install install-dev test lint types check format run-api run-ui clean

help:  ## Show this help
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package
	pip install -e "."

install-dev:  ## Install with web and dev extras, as CI does
	pip install -r requirements.txt -r requirements-dev.txt
	pip install -e ".[web]"

test:  ## Run the test suite
	pytest tests/

lint:  ## Check formatting and lint rules
	ruff check src/ tests/

types:  ## Type-check the package
	mypy src/ --ignore-missing-imports

check: lint types test  ## Everything CI runs

format:  ## Apply automatic fixes
	ruff check src/ tests/ --fix

run-api:  ## Serve the REST API on :8000
	python -m uvicorn cribl_hc.api.app:app --reload --port 8000

run-ui:  ## Serve the web UI on :5173
	cd frontend && npm run dev

clean:  ## Remove build and test artifacts
	rm -rf build/ dist/ htmlcov/ .coverage coverage.xml .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -not -path "./node_modules/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -not -path "./node_modules/*" -exec rm -rf {} + 2>/dev/null || true
