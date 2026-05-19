from migrator_gen import MigrationClient, Rule, ChangeType
client = MigrationClient(mode='local')
# Check health
print('Health:', client.health_check().status)
# Transform code
result = client.migrate_code(
    'def old_func(): pass',
    [Rule(id='R1', change_type=ChangeType.RENAME_FUNCTION,
          version_introduced='2.0.0', description='Rename',
          old_name='old_func', new_name='new_func')],
)
print('Transformed:', result.transformed_code)
# Preview diff
preview = client.preview_migration(
    'def old_func(): pass',
    [Rule(id='R1', change_type=ChangeType.RENAME_FUNCTION,
          version_introduced='2.0.0', description='Rename',
          old_name='old_func', new_name='new_func')],
)
print('Diff:', preview.diff)