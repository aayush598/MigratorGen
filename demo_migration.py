import json
from pathlib import Path
from core.changelog_parser import ChangelogParser, MigrationRule, ChangeType
from core.version_resolver import VersionResolver
from core.migration_engine import MigrationEngine
from core.migrator_generator import MigratorGenerator

# Load example JSON changelog
content = Path('examples/mylib_changelog.json').read_text()
parser = ChangelogParser()
changelogs = parser.parse(content, fmt='json')
print(f'Parsed {len(changelogs)} versions')

# Show rules
for vc in changelogs:
    print(f'  v{vc.version}: {len(vc.rules)} rules')

# Resolve path 1.0.0 -> 3.0.0
resolver = VersionResolver(changelogs)
path = resolver.resolve_path('1.0.0', '3.0.0')
print(f'\nMigration path: {path.source_version} -> {path.target_version}')
print(f'Rules to apply: {len(path.rules)}')
for r in path.rules:
    print(f'  [{r.change_type.value}] {r.description}')

# Apply to sample code
sample_code = Path('examples/sample_user_code.py').read_text()
engine = MigrationEngine()
result = engine.migrate_code(sample_code, path.rules)

print(f'\nTransformation result:')
print(f'  Modified: {result.was_modified}')
print(f'  Changes: {len(result.changes)}')
for c in result.changes:
    print(f'  ✓ {c}')

print('\n--- Migrated Code ---')
print(result.transformed_code)