
import pytest

from migrator_gen import ChangeType, MigrationFile, Rule, VersionChangelog


@pytest.fixture
def sample_rule() -> Rule:
    return Rule(
        id="R001",
        change_type=ChangeType.RENAME_FUNCTION,
        version_introduced="2.0.0",
        description="Rename old_func to new_func",
        old_name="old_func",
        new_name="new_func",
    )


@pytest.fixture
def sample_rules() -> list[Rule]:
    return [
        Rule(id="R1", change_type=ChangeType.RENAME_FUNCTION, version_introduced="2.0.0",
             description="Rename a to b", old_name="a", new_name="b"),
        Rule(id="R2", change_type=ChangeType.ADD_ARGUMENT, version_introduced="2.0.0",
             description="Add timeout to connect", function_name="connect",
             argument_name="timeout", default_value="30"),
    ]


@pytest.fixture
def sample_changelog() -> VersionChangelog:
    return VersionChangelog(
        version="2.0.0",
        release_date="2024-01-15",
        rules=[
            Rule(id="V1", change_type=ChangeType.RENAME_FUNCTION, version_introduced="2.0.0",
                 description="Rename x to y", old_name="x", new_name="y"),
        ],
    )


@pytest.fixture
def sample_migration_file() -> MigrationFile:
    return MigrationFile(
        library="testlib",
        schema_version="1.0",
        versions=[
            VersionChangelog(
                version="2.0.0",
                rules=[
                    Rule(id="M1", change_type=ChangeType.RENAME_FUNCTION, version_introduced="2.0.0",
                         description="Rename foo to bar", old_name="foo", new_name="bar"),
                ],
            ),
        ],
    )
