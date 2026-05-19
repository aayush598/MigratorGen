"""Using SyncMigrationClient — the main entry point for local and remote use."""
from migrator_gen import SyncMigrationClient, Rule, ChangeType

# Auto-detection — install libcst for local mode, or set base_url for remote
with SyncMigrationClient(mode="local") as client:
    print(f"Mode: {client.mode}")

    code = "result = fetch_data()"
    rules = [
        Rule(id="R1", change_type=ChangeType.RENAME_FUNCTION,
             old_name="fetch_data", new_name="get_data",
             description="fetch_data → get_data"),
    ]

    # migrate_code — returns a MigrateResponse
    resp = client.migrate_code(code, rules)
    print(f"Transformed code:\n{resp.transformed_code}")

    # Preview without modifying
    preview = client.preview_migration(code, rules)
    print(f"Diff preview:\n{preview.diff}")

    # Preview diff
    preview = client.preview_migration(code, rules)
    print(f"Diff:\n{preview.diff}")
    print(f"Changes count: {preview.change_count}")

# Remote usage (requires a running migrator-gen API server):
# with SyncMigrationClient(mode="remote", base_url="http://localhost:8000") as client:
#     libs = client.list_libraries()
#     status = client.health_check()
