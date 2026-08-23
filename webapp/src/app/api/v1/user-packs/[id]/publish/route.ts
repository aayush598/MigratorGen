import { NextResponse } from "next/server";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { USER_PACKS_DIR } from "@/lib/packs";
import { requireSession, errorResponse } from "@/lib/api-helpers";

interface RouteContext {
  params: { id: string };
}

export async function POST(_request: Request, context: RouteContext) {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    const packId = context.params.id;
    const filePath = path.join(USER_PACKS_DIR, `${packId}.json`);
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(await readFile(filePath, "utf-8")) as Record<string, unknown>;
    } catch {
      return NextResponse.json({ error: "Pack not found" }, { status: 404 });
    }

    data.is_published = !(data.is_published as boolean);
    data.updated_at = new Date().toISOString();
    await writeFile(filePath, JSON.stringify(data, null, 2), "utf-8");

    return NextResponse.json({
      status: data.is_published ? "published" : "unpublished",
      id: packId,
    });
  } catch (err) {
    return errorResponse(err);
  }
}

export const runtime = "nodejs";
