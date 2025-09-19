.PHONY: help quickstart install install-dev clean test lint format check venv run

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
	@echo "  make test          - Run all tests"
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
	@echo "Starting MCP Chart Signals server with crypto + storage..."
	@echo "Loading symbols from watchlist.txt..."
	@$(UV) run --python $(VENV) python ta_server_full.py

run-stocks:
	@echo "Starting MCP Chart Signals server (stocks only)..."
	@echo "Loading symbols from watchlist.txt..."
	@$(UV) run --python $(VENV) python ta_server_alpaca.py

run-basic:
	@echo "Starting basic MCP server (webhook-based)..."
	@$(UV) run --python $(VENV) python ta_server.py

test:
	@echo "Running tests..."
	@if [ -d "tests" ] && [ -n "$$(ls -A tests 2>/dev/null)" ]; then \
		$(UV) run --python $(VENV) pytest tests -v; \
	else \
		echo "No tests found"; \
	fi

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
