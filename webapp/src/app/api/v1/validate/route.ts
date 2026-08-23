import { NextResponse } from "next/server";
import { validateRules, EngineError } from "@/lib/pyodide";
import { errorResponse } from "@/lib/api-helpers";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as {
      rules_path?: string;
      rules_content?: Record<string, unknown>;
    };

    if (!body.rules_content) {
      return NextResponse.json(
        { error: "rules_content is required" },
        { status: 422 },
      );
    }

    const result = await validateRules(body.rules_content);
    return NextResponse.json({
      valid: result.valid ?? false,
      error_count: result.error_count ?? result.errors?.length ?? 0,
      warning_count: result.warning_count ?? result.warnings?.length ?? 0,
      info_count: result.info_count ?? result.info?.length ?? 0,
      errors: result.errors ?? [],
      warnings: result.warnings ?? [],
      info: result.info ?? [],
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
