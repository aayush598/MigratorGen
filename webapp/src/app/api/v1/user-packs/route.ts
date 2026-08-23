import { NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { getDb } from "@/lib/db";
import { userPacks } from "@/lib/db-schema";
import { listUserPacks } from "@/lib/packs";
import { requireSession, errorResponse } from "@/lib/api-helpers";

export async function GET() {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    const packs = await listUserPacks();
    return NextResponse.json({ packs });
  } catch (err) {
    return errorResponse(err);
  }
}

export async function POST(request: Request) {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    const body = (await request.json()) as {
      name?: string;
      description?: string;
      library?: string;
      versions?: unknown[];
    };
    if (!body.name || !body.library) {
      return NextResponse.json({ error: "name and library are required" }, { status: 422 });
    }

    const db = getDb();
    const packId = randomUUID().slice(0, 8);
    const now = new Date().toISOString();

    await db.insert(userPacks).values({
      id: packId,
      userId: auth.session.userId,
      name: body.name,
      description: body.description ?? "",
      library: body.library,
      schemaVersion: "1.0",
      isPublished: false,
      createdAt: now,
      updatedAt: now,
      versions: body.versions ?? [],
    });

    return NextResponse.json({
      id: packId,
      name: body.name,
      library: body.library,
      description: body.description ?? "",
      version_count: body.versions?.length ?? 0,
      created_at: now,
    });
  } catch (err) {
    return errorResponse(err);
  }
}

export const runtime = "nodejs";
