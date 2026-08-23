import { NextResponse } from "next/server";
import { migrateCode, EngineError } from "@/lib/pyodide";
import { errorResponse } from "@/lib/api-helpers";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      source_code?: string;
      rules?: Record<string, unknown>[];
      source_version?: string;
      target_version?: string;
      dry_run?: boolean;
    };

    if (typeof body.source_code !== "string") {
      return NextResponse.json({ error: "source_code is required" }, { status: 422 });
    }

    const rules = Array.isArray(body.rules) ? body.rules : [];
    const targetVersion = body.target_version || "latest";

    const result = await migrateCode(body.source_code, rules, targetVersion);

    return NextResponse.json({
      original_code: result.original_code ?? "",
      transformed_code: result.transformed_code ?? "",
      changes: result.changes ?? [],
      change_count: result.change_count ?? 0,
      rules_applied: result.rules_applied ?? [],
      average_confidence: result.average_confidence ?? 0,
      was_modified: result.was_modified ?? false,
      errors: result.errors ?? [],
      duration_ms: result.duration_ms,
    });
  } catch (err) {
    if (err instanceof EngineError) {
      return NextResponse.json({ error: err.message }, { status: 422 });
    }
    return errorResponse(err);
  }
}

export const runtime = "nodejs";
export const maxDuration = 60;
