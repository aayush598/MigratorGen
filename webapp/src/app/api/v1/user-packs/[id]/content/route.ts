import { NextResponse } from "next/server";
import { getUserPackById } from "@/lib/packs";
import { requireSession, errorResponse } from "@/lib/api-helpers";

interface RouteContext {
  params: { id: string };
}

export async function GET(_request: Request, context: RouteContext) {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    const packId = context.params.id;
    const packData = await getUserPackById(packId);
    if (!packData) return NextResponse.json({ error: "Pack not found" }, { status: 404 });

    const library = (packData.library as string) ?? packId;
    const name = (packData.name as string) ?? library;
    const description = (packData.description as string) ?? "";
    const versions = (packData.versions as Array<{ version: string; rules: unknown[] }>) ?? [];

    const packJson = {
      library,
      name,
      description,
      schema_version: "1.0",
      versions,
    };

    return NextResponse.json(packJson, {
      headers: {
        "Content-Type": "application/json",
        "Content-Disposition": `inline; filename="migration-pack.json"`,
      },
    });
  } catch (err) {
    return errorResponse(err);
  }
}

export const runtime = "nodejs";
