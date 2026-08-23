import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { getDb } from "@/lib/db";
import { userPacks } from "@/lib/db-schema";
import { getUserPackById } from "@/lib/packs";
import { requireSession, errorResponse } from "@/lib/api-helpers";

interface RouteContext {
  params: { id: string };
}

export async function POST(_request: Request, context: RouteContext) {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    const packId = context.params.id;
    const existing = await getUserPackById(packId);
    if (!existing) return NextResponse.json({ error: "Pack not found" }, { status: 404 });

    const newPublished = !(existing.is_published as boolean);
    const db = getDb();
    await db
      .update(userPacks)
      .set({ isPublished: newPublished, updatedAt: new Date().toISOString() })
      .where(eq(userPacks.id, packId));

    return NextResponse.json({
      status: newPublished ? "published" : "unpublished",
      id: packId,
    });
  } catch (err) {
    return errorResponse(err);
  }
}

export const runtime = "nodejs";
