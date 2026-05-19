from __future__ import annotations

from enum import Enum


class ChangeType(str, Enum):
    RENAME_FUNCTION = "rename_function"
    RENAME_CLASS = "rename_class"
    RENAME_ATTRIBUTE = "rename_attribute"
    RENAME_IMPORT = "rename_import"
    RENAME_MODULE = "rename_module"
    RENAME_PARAMETER = "rename_parameter"
    RENAME_ARGUMENT = "rename_argument"
    ADD_ARGUMENT = "add_argument"
    REMOVE_ARGUMENT = "remove_argument"
    CHANGE_ARGUMENT_DEFAULT = "change_argument_default"
    CHANGE_TYPE_ANNOTATION = "change_type_annotation"
    REORDER_ARGUMENTS = "reorder_arguments"
    DEPRECATE_FUNCTION = "deprecate_function"
    DEPRECATE_CLASS = "deprecate_class"
    DEPRECATE_MODULE = "deprecate_module"
    DEPRECATE_PARAMETER = "deprecate_parameter"
    REMOVE_FUNCTION = "remove_function"
    REMOVE_CLASS = "remove_class"
    REPLACE_WITH_PROPERTY = "replace_with_property"
    MOVE_TO_MODULE = "move_to_module"
    MOVE_TO_SUBMODULE = "move_to_submodule"
    MOVE_CLASS_TO_MODULE = "move_class_to_module"
    ADD_DECORATOR = "add_decorator"
    REMOVE_DECORATOR = "remove_decorator"
    CHANGE_DECORATOR = "change_decorator"
    SYNC_TO_ASYNC = "sync_to_async"
    ASYNC_TO_SYNC = "async_to_sync"
    WRAP_IN_CONTEXT_MANAGER = "wrap_in_context_manager"
    WRAP_IN_SYNC_CONTEXT_MANAGER = "wrap_in_sync_context_manager"
    CLASS_SPLIT = "class_split"
    MODULE_SPLIT = "module_split"
    MERGE_CLASSES = "merge_classes"
    MERGE_MODULES = "merge_modules"
    CHANGE_RETURN_TYPE = "change_return_type"
    ENUM_MIGRATION = "enum_migration"
    CHANGE_ENUM_BASE = "change_enum_base"
    DATACLASS_FIELD_ADD = "dataclass_field_add"
    DATACLASS_FIELD_REMOVE = "dataclass_field_remove"
    DATACLASS_FIELD_RENAME = "dataclass_field_rename"
    DATACLASS_FIELD_CHANGE = "dataclass_field_change"


class SafetyLevel(str, Enum):
    SAFE = "safe"
    REVIEW_REQUIRED = "review_required"
    RISKY = "risky"


class MigrationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class EngineMode(str, Enum):
    AUTO = "auto"
    LOCAL = "local"
    REMOTE = "remote"
