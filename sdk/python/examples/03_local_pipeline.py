"""
Complete local pipeline:
  Changelog → resolve migration path → migrate code → validate report.

Uses the core engine directly without the client wrapper.
"""
from migrator_gen.core.changelog_parser import ChangelogParser
from migrator_gen.core.version_resolver import VersionResolver
from migrator_gen.core.migration_engine import TransactionalMigrationEngine
from migrator_gen.core.validation import RuleValidator

changelog_json = """
{
  "library": "demo",
  "versions": [
    {
      "version": "2.0.0",
      "release_date": "2025-01-01",
      "rules": [
        {"id": "D-001", "change_type": "rename_function",
         "version_introduced": "2.0.0",
         "description": "connect → create_connection",
         "old_name": "connect", "new_name": "create_connection"},
        {"id": "D-002", "change_type": "rename_attribute",
         "version_introduced": "2.0.0",
         "description": "url → base_url",
         "old_name": "url", "new_name": "base_url"}
      ]
    }
  ]
}
"""

# 1. Parse
parser = ChangelogParser()
changelogs = parser.parse(changelog_json, fmt="json")
print(f"Parsed {len(changelogs)} version(s)")

# 2. Resolve migration path
resolver = VersionResolver(changelogs)
path = resolver.resolve_path("1.0.0", "2.0.0")
print(f"Path: {path.source_version} → {path.target_version}")
print(f"Rules to apply: {len(path.rules)}")

# 3. Validate rules
validator = RuleValidator()
report = validator.validate_rules(path.rules)
print(f"Rules valid: {report.valid}")

# 4. Run migration
code = """
from demo import connect
c = connect()
print(c.url)
"""
engine = TransactionalMigrationEngine()
result = engine.migrate_code(code, path.rules)

print(f"\nModified: {result.was_modified}")
print(f"Changes made: {len(result.changes)}")
for c in result.changes:
    print(f"  - {c}")
print(f"\n--- Output ---\n{result.transformed_code}")
