#!/usr/bin/env bash

# Run tests using pytest

echo "Installing dev dependencies..."
uv pip install -e .[dev] || {
    echo "Failed to install with [dev] extras, trying dev-dependencies..."
    uv sync --dev
}

echo ""
echo "Running pytest..."
pytest tests/ -v --tb=short

echo ""
echo "For coverage report, run:"
echo "  pytest tests/ --cov=rcplxd --cov-report=html"