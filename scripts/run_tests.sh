#!/usr/bin/env bash

# Run tests using pytest

cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

echo "Installing dev dependencies..."
uv sync --group dev

echo ""
echo "Running pytest..."
pytest tests/ -v --tb=short

echo ""
echo "For coverage report, run:"
echo "  pytest tests/ --cov=rcplxd --cov-report=html"