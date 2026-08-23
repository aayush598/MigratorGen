"""
Using LibCST-based transformers directly for fine-grained control.
"""

import libcst as cst

from migrator_gen.core.changelog_parser import ChangeType, MigrationRule
from migrator_gen.core.migration_engine import TransactionalMigrationEngine
from migrator_gen.core.transformers import get_transformer

# --- Direct transformer usage ---
code = """
def handle_event(event):
    print(f"Got: {event}")
"""

# Create a rule and get the matching transformer
rule = MigrationRule(
    id="ADV-001",
    change_type=ChangeType.ADD_DECORATOR,
    description="add @handler decorator",
    version_introduced="2.0.0",
    function_name="handle_event",
    decorator_name="handler",
)

transformer = get_transformer(rule)
tree = cst.parse_module(code)
modified_tree = tree.visit(transformer)
print("--- With decorator ---")
print(modified_tree.code)

# --- Using the migration engine with advanced features ---
engine = TransactionalMigrationEngine(
    transactional=True,  # roll back on error
    interactive_approval=False,  # auto-approve
    idempotency_check=True,  # skip unchanged files
)

code = """
from mylib import OldName

class Controller:
    def run(self):
        return OldName()
"""

rules = [
    MigrationRule(
        id="ADV-002",
        change_type=ChangeType.RENAME_CLASS,
        description="OldName → NewName",
        version_introduced="2.0.0",
        old_name="OldName",
        new_name="NewName",
        safety="safe",
    ),
]

result = engine.migrate_code(code, rules)
print("--- Engine migration ---")
print(f"Modified: {result.was_modified}")
print(f"Result:\n{result.transformed_code}")

# --- Validate before applying ---
from migrator_gen.core.validation import RuleValidator

validator = RuleValidator()
report = validator.validate_rules(rules)
print(f"Valid: {report.valid}")
if report.errors:
    for err in report.errors:
        print(f"  Error: {err}")
