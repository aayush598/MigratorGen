"""Minimal working migration example — create rules and migrate code."""
from migrator_gen import Rule, ChangeType, SafetyLevel, SyncMigrationClient

code = """
from mylib import Client
client = Client()
result = client.get_name()
"""

rules = [
    Rule(id="R1", change_type=ChangeType.RENAME_CLASS,
         old_name="Client", new_name="APIClient",
         description="Client → APIClient",
         safety=SafetyLevel.SAFE),
    Rule(id="R2", change_type=ChangeType.REPLACE_WITH_PROPERTY,
         old_name="get_name", new_name="name",
         function_name="Client",
         description="get_name() → .name property"),
]

with SyncMigrationClient(mode="local") as client:
    result = client.migrate_code(code, rules)
    print(f"Modified: {result.was_modified}")
    print(result.transformed_code)
