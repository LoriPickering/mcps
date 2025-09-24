.PHONY: help quickstart install install-dev clean test test-mcp test-all test-quick docs clean-cache lint format check venv run

PYTHON_VERSION := 3.12
VENV := .venv
UV := uv

help:
	@echo "Available commands:"
	@echo "  make quickstart    - Set up Python environment and install dependencies"
	@echo "  make install       - Install project dependencies"
	@echo "  make install-dev   - Install development dependencies"
	@echo "  make run           - Start the MCP server"
	@echo "  make clean         - Remove virtual environment and cache files"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run code-based unit tests"
	@echo "  make test-mcp      - Run MCP server tests only"
	@echo "  make test-all      - Run ALL tests (unit + MCP + integration)"
	@echo "  make test-quick    - Quick MCP health check"
	@echo "  make docs          - Check documentation"
	@echo "  make clean-cache   - Remove __pycache__ files"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run linting checks"
	@echo "  make format        - Format code"
	@echo "  make check         - Run all checks (lint + test)"
	@echo "  make venv          - Create virtual environment only"

quickstart:
	@echo "🚀 Starting quickstart setup..."
	@echo "📦 Installing uv if not present..."
	@command -v $(UV) >/dev/null 2>&1 || (echo "Installing uv..." && curl -LsSf https://astral.sh/uv/install.sh | sh)
	@echo "🐍 Creating Python $(PYTHON_VERSION) virtual environment..."
	@$(UV) venv --python $(PYTHON_VERSION) $(VENV)
	@echo "📌 Bootstrapping pip in virtual environment..."
	@$(UV) pip install --python $(VENV) pip
	@echo "📚 Installing project dependencies..."
	@$(UV) pip sync --python $(VENV) requirements.txt 2>/dev/null || $(UV) pip install --python $(VENV) -e .
	@echo "🔧 Installing development dependencies..."
	@$(UV) pip install --python $(VENV) -e ".[dev]"
	@echo ""
	@echo "✅ Quickstart complete!"
	@echo ""
	@echo "Activate the environment with:"
	@echo "  source $(VENV)/bin/activate"
	@echo ""
	@echo "Or run commands directly with uv:"
	@echo "  $(UV) run --python $(VENV) python your_script.py"

venv:
	@echo "Creating virtual environment with Python $(PYTHON_VERSION)..."
	@$(UV) venv --python $(PYTHON_VERSION) $(VENV)

install: venv
	@echo "Installing project dependencies..."
	@$(UV) pip install --python $(VENV) pip
	@$(UV) pip install --python $(VENV) -e .

install-dev: install
	@echo "Installing development dependencies..."
	@$(UV) pip install --python $(VENV) -e ".[dev]"

clean:
	@echo "Cleaning up..."
	@rm -rf $(VENV)
	@rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "Clean complete!"

run:
	@echo "Starting Trading Data Collector (Alpaca + Storage)..."
	@echo "Loading symbols from watchlist.txt..."
	@$(UV) run --python $(VENV) python servers/trading/ta_server_full.py

run-trading-mcp:
	@echo "Testing Trading MCP Server..."
	@$(UV) run --python $(VENV) python servers/trading/mcp_server_integrated.py

test:
	@echo "Running code-based unit tests..."
	@echo "=========================================="
	@if [ -d "tests" ]; then \
		PYTHONPATH=$(PWD) $(VENV)/bin/python -m pytest tests/test_indicators.py tests/test_integration.py -v --tb=short; \
	else \
		echo "No tests found"; \
	fi

test-mcp:
	@echo "Running MCP server tests..."
	@echo "=========================================="
	@PYTHONPATH=$(PWD) $(VENV)/bin/python -m pytest tests/test_mcp_server.py tests/integration/test_mcp_darpa_integration.py -v --tb=short

test-all:
	@echo "Running ALL tests (unit + MCP + integration)..."
	@echo "=========================================="
	@if [ -x "scripts/test_all_mcp.sh" ]; then \
		./scripts/test_all_mcp.sh; \
	else \
		PYTHONPATH=$(PWD) $(VENV)/bin/python -m pytest tests/ -v --tb=short; \
	fi

test-quick:
	@echo "Quick MCP health check..."
	@echo "=========================================="
	@PYTHONPATH=$(PWD) $(VENV)/bin/python scripts/test_mcp_health.py --quick

test-summary:
	@echo "Test Suite Summary:"
	@echo "=========================================="
	@echo "Available test commands:"
	@echo "  make test        - Unit tests (indicators, integration)"
	@echo "  make test-mcp    - MCP server tests only"
	@echo "  make test-all    - Complete test suite"
	@echo "  make test-quick  - Quick health check (4 tests)"
	@echo ""
	@echo "Test file locations:"
	@echo "  Unit tests:       tests/test_indicators.py"
	@echo "  MCP tests:        tests/test_mcp_server.py"
	@echo "  Integration:      tests/integration/"
	@echo "  Health check:     scripts/test_mcp_health.py"
	@echo ""
	@echo "Run 'make test-quick' for a fast system check"

docs:
	@echo "Checking documentation..."
	@if [ -d "docs" ]; then \
		echo "Documentation directory found"; \
		ls -la docs/; \
	else \
		echo "No docs directory found"; \
	fi

clean-cache:
	@echo "Removing __pycache__ files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@rm -rf .pytest_cache .mypy_cache .ruff_cache
	@echo "Cache cleanup complete!"

lint:
	@echo "Running linting checks..."
	@$(UV) run --python $(VENV) ruff check *.py
	@$(UV) run --python $(VENV) mypy *.py --ignore-missing-imports

format:
	@echo "Formatting code..."
	@$(UV) run --python $(VENV) black *.py
	@$(UV) run --python $(VENV) isort *.py
	@$(UV) run --python $(VENV) ruff check --fix *.py

check: lint test
	@echo "All checks passed!"
