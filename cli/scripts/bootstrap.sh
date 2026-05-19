#!/usr/bin/env bash
set -euo pipefail

echo "🔧 Installing migrator-gen SDK ..."
pip install -e "$(dirname "$0")/../../sdk/python[all]"

echo "🔧 Installing CLI ..."
pip install -e "$(dirname "$0")/..[dev]"

echo "✅ migrator-gen CLI ready"
migrator-gen --version
