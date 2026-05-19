"""MigratorGen MCP Server — Model Context Protocol for IDE and tool integration.

Tools
-----
- generate_rules          Generate migration rules from changelog / diff
- preview_migration       Dry-run a migration and return the diff
- run_migration           Apply migration rules to source code
- validate_rules          Validate migration rules from a file
- analyze_code            Extract imports / functions / classes from code
- suggest_migrations      Suggest applicable migrations for a codebase
- create_migrator         Generate a standalone pip-installable migrator package
- list_libraries          List libraries with available migration packs
- explain_breaking_changes  Explain breaking changes in a migration rule-set
- resolve_path            Resolve migration path between two versions
"""

from .version import VERSION, __version__

__all__ = ["VERSION", "__version__"]
