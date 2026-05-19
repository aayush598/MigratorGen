#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing dependencies..."
pip install -e ".[dev]"

echo "==> Running tests..."
python -m pytest tests/ -v --tb=short

echo "==> Done!"
