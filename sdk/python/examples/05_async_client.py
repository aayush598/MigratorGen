"""
Async MigrationClient — context manager based, the primary SDK client.
"""
import asyncio
from migrator_gen import MigrationClient, Rule, ChangeType

async def main():
    async with MigrationClient(mode="local") as client:
        print(f"Mode: {client.mode}")
        print(f"Config timeout: {client.config.timeout}s")

        code = "from mylib import Client; c = Client()"
        rules = [
            Rule(id="R1", change_type=ChangeType.RENAME_CLASS,
                 old_name="Client", new_name="APIClient",
                 description="Client → APIClient"),
        ]

        resp = await client.migrate_code(code, rules)
        print(f"Result:\n{resp.transformed_code}")

        # Preview diff
        preview = await client.preview_migration(code, rules)
        print(f"Diff:\n{preview.diff}")

asyncio.run(main())
