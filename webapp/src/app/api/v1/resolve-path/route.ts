import { NextResponse } from "next/server";
import path from "node:path";
import { readFile } from "node:fs/promises";
import { resolvePath, EngineError } from "@/lib/pyodide";
import { errorResponse } from "@/lib/api-helpers";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      source_version?: string;
      target_version?: string;
      library_name?: string;
    };
    if (!body.library_name) {
      return NextResponse.json({ error: "library_name is required" }, { status: 422 });
    }

    let changelogJson = JSON.stringify({ versions: [] });
    try {
      const packsDir = path.resolve(process.cwd(), "..", "migration-packs");
      const packPath = path.join(packsDir, `${body.library_name}.json`);
      changelogJson = await readFile(packPath, "utf-8");
    } catch {
      // unknown library — resolve against an empty changelog
    }

    const result = await resolvePath(
      body.source_version ?? "0.0.0",
      body.target_version ?? "latest",
      changelogJson,
    );

    return NextResponse.json(result);
  } catch (err) {
    if (err instanceof EngineError) {
      return NextResponse.json({ error: err.message }, { status: 422 });
    }
    return errorResponse(err);
  }
}

export const runtime = "nodejs";
export const maxDuration = 60;
