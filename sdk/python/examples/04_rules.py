"""
Creating, serialising, and inspecting Rule objects.
"""

from migrator_gen import (
    ChangeType,
    EngineMode,
    Rule,
    RuleWhenCondition,
    SafetyLevel,
)

# --- Create rules ---
rules = [
    Rule(
        id="REN-001",
        change_type=ChangeType.RENAME_FUNCTION,
        description="connect → create_connection",
        old_name="connect",
        new_name="create_connection",
        version_introduced="2.0.0",
        safety=SafetyLevel.SAFE,
        idempotent_safe=True,
    ),
    Rule(
        id="DEP-001",
        change_type=ChangeType.DEPRECATE_FUNCTION,
        description="fetch_data is deprecated",
        old_name="fetch_data",
        replacement="get_data",
        version_introduced="1.5.0",
        safety=SafetyLevel.SAFE,
    ),
    Rule(
        id="ARG-001",
        change_type=ChangeType.ADD_ARGUMENT,
        description="Added timeout to create_connection",
        function_name="create_connection",
        argument_name="timeout",
        default_value="30",
        safety=SafetyLevel.REVIEW_REQUIRED,
    ),
    Rule(
        id="MOVE-001",
        change_type=ChangeType.MOVE_TO_MODULE,
        description="Formatter moved to mylib.utils",
        old_name="Formatter",
        source_module="mylib.helpers",
        target_module="mylib.utils",
    ),
    Rule(
        id="WHEN-001",
        change_type=ChangeType.RENAME_CLASS,
        description="OldName renamed",
        old_name="OldName",
        new_name="NewName",
        when=RuleWhenCondition(
            imported_from="mylib",
            inside_class="Controller",
        ),
    ),
]

# --- Serialise to dict / JSON ---
for rule in rules:
    print(f"{rule.id: >8} | {rule.change_type: <25} | {rule.description}")
    d = rule.to_dict()
    restored = Rule.from_dict(d)
    assert restored.id == rule.id
    assert restored.change_type == rule.change_type

# --- Filter by safety ---
risky = [r for r in rules if r.safety == SafetyLevel.REVIEW_REQUIRED]
print(f"\nRules requiring review: {len(risky)}")

# --- Use with EngineMode ---
print(f"Engine modes: {[e.value for e in EngineMode]}")
