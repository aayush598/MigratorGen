#!/usr/bin/env bash
set -euo pipefail

# 1. Create a migrator from a changelog
migrator-gen create \
  --changelog ../../examples/mylib_changelog.json \
  --library mylib \
  --output ./out

# 2. Preview migration on a file
migrator-gen preview ../../examples/sample_user_code.py \
  --rules ./out/migration_rules.json

# 3. Run migration
migrator-gen run ../../examples/sample_user_code.py \
  --rules ./out/migration_rules.json

# 4. List rules
migrator-gen rules --rules ./out/migration_rules.json
