#!/usr/bin/env bash
set -euo pipefail

# 1. Validate rules file
migrator-gen validate-rules ./out/migration_rules.json

# 2. Diff two rule sets
migrator-gen diff-rules \
  --old ./out/migration_rules.json \
  --new ./updated_rules.json

# 3. Audit a project
migrator-gen audit ./my_project \
  --rules ./out/migration_rules.json

# 4. Auto-detect dependencies
migrator-gen auto-upgrade ./my_project --json
