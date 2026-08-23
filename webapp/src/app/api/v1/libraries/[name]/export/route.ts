import { NextResponse } from "next/server";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import JSZip from "jszip";
import { getBuiltinPack } from "@/lib/packs";

interface RouteContext {
  params: { name: string };
}

const ENGINE_DIR = path.resolve(process.cwd(), "..", "sdk", "python", "src", "migrator_gen", "core");
const SDK_VERSION = "0.2.0";

async function readEngineFiles(): Promise<Record<string, string>> {
  const files: Record<string, string> = {};
  const entries = await readdir(ENGINE_DIR);
  for (const entry of entries) {
    if (!entry.endsWith(".py")) continue;
    const content = await readFile(path.join(ENGINE_DIR, entry), "utf-8");
    files[entry] = content;
  }
  return files;
}

export async function GET(_request: Request, context: RouteContext) {
  try {
    const library = decodeURIComponent(context.params.name);
    const packData = await getBuiltinPack(library);
    if (!packData) {
      return NextResponse.json({ error: `Library '${library}' not found` }, { status: 404 });
    }

    const safeName = library.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    const versions = packData.versions ?? [];
    const ruleCount = versions.reduce((sum, v) => sum + (v.rules?.length ?? 0), 0);

    const zip = new JSZip();
    const engineFiles = await readEngineFiles();

    for (const [filename, content] of Object.entries(engineFiles)) {
      zip.file(`${safeName}_migration/engine/${filename}`, content);
    }

    const packJson = {
      library,
      name: library,
      description: packData.description ?? "",
      schema_version: "1.0",
      versions,
    };
    zip.file(`${safeName}_migration/engine/__init__.py`, "");
    zip.file(`${safeName}_migration/__init__.py`, `"""${library} migration pack."""\n`);
    zip.file(`${safeName}_migration/migration-pack.json`, JSON.stringify(packJson, null, 2));
    zip.file(`${safeName}_migration/cli.py`, `"""CLI entry point for ${library} migration pack."""\n\nfrom __future__ import annotations\n\nimport argparse\nimport json\nimport sys\nfrom pathlib import Path\n\n\ndef main() -> None:\n    parser = argparse.ArgumentParser(description="${library} migration tool")\n    parser.add_argument("--source", "-s", required=True, help="Source file to migrate")\n    parser.add_argument("--target-version", "-t", default="latest")\n    parser.add_argument("--pack", default="migration-pack.json")\n    parser.add_argument("--output", "-o")\n    parser.add_argument("--dry-run", action="store_true")\n    args = parser.parse_args()\n\n    source = Path(args.source).read_text()\n    rules = json.loads(Path(args.pack).read_text())\n    all_rules = [r for v in rules.get("versions", []) for r in v.get("rules", [])]\n\n    try:\n        from migrator_gen import SyncMigrationClient\n        client = SyncMigrationClient()\n        result = client.migrate(source_code=source, rules=json.dumps(all_rules), target_version=args.target_version)\n        if args.dry_run:\n            print(result.transformed_code)\n        elif args.output:\n            Path(args.output).write_text(result.transformed_code)\n        else:\n            print(result.transformed_code)\n    except ImportError:\n        print("pip install migrator-gen", file=sys.stderr)\n        sys.exit(1)\n\n\nif __name__ == "__main__":\n    main()\n`);

    zip.file(
      "pyproject.toml",
      `[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n\n[project]\nname = "${safeName}-migration"\nversion = "${SDK_VERSION}"\ndescription = "Migration rules for ${library}"\nreadme = "README.md"\nrequires-python = ">=3.10"\nlicense = "MIT"\ndependencies = [\n    "migrator-gen>=${SDK_VERSION}",\n    "libcst>=1.0.0",\n    "pydantic>=2.0.0",\n]\n\n[project.scripts]\n${safeName}-migrate = "${safeName}_migration.cli:main"\n\n[tool.hatch.build.targets.wheel]\npackages = ["${safeName}_migration"]\n`,
    );

    zip.file(
      "README.md",
      `# ${library} Migration Pack\n\nAutomated migration rules for ${library}.\n\n## Install\n\n\`\`\`bash\npip install -e .\n\`\`\`\n\n## Usage\n\n\`\`\`bash\n${safeName}-migrate --source my_code.py --target-version 2.0.0\n\`\`\`\n\n## Rules\n\n${ruleCount} rules across ${versions.length} version(s).\n`,
    );

    const buffer = await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });

    return new NextResponse(new Uint8Array(buffer), {
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": `attachment; filename="${safeName}-migration-pack.zip"`,
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export const runtime = "nodejs";
