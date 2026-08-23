import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { getDb } from "@/lib/db";
import { userPacks } from "@/lib/db-schema";
import { getUserPackById } from "@/lib/packs";
import { requireSession, errorResponse } from "@/lib/api-helpers";

interface RouteContext {
  params: { id: string };
}

export async function GET(_request: Request, context: RouteContext) {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    const data = await getUserPackById(context.params.id);
    if (!data) return NextResponse.json({ error: "Pack not found" }, { status: 404 });

    const versions = (data.versions as unknown[]) ?? [];
    return NextResponse.json({
      id: context.params.id,
      name: (data.name as string) ?? context.params.id,
      description: (data.description as string) ?? "",
      library: (data.library as string) ?? context.params.id,
      versions,
      version_count: versions.length,
      rule_count: versions.reduce(
        (sum: number, v) => sum + (((v as Record<string, unknown>).rules as unknown[])?.length ?? 0),
        0,
      ),
      is_published: (data.is_published as boolean) ?? false,
      created_at: (data.created_at as string) ?? "",
      updated_at: (data.updated_at as string) ?? "",
    });
  } catch (err) {
    return errorResponse(err);
  }
}

export async function PUT(request: Request, context: RouteContext) {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    const packId = context.params.id;
    const existing = await getUserPackById(packId);
    if (!existing) return NextResponse.json({ error: "Pack not found" }, { status: 404 });

    const body = (await request.json()) as {
      name?: string;
      description?: string;
      versions?: unknown[];
    };

    const db = getDb();
    const updates: Record<string, unknown> = { updatedAt: new Date().toISOString() };
    if (body.name !== undefined) updates.name = body.name;
    if (body.description !== undefined) updates.description = body.description;
    if (body.versions !== undefined) updates.versions = body.versions;

    await db.update(userPacks).set(updates).where(eq(userPacks.id, packId));
    return NextResponse.json({ status: "updated", id: packId });
  } catch (err) {
    return errorResponse(err);
  }
}

export async function DELETE(_request: Request, context: RouteContext) {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    const db = getDb();
    const result = await db.delete(userPacks).where(eq(userPacks.id, context.params.id));
    if (result.rowCount === 0) {
      return NextResponse.json({ error: "Pack not found" }, { status: 404 });
    }
    return NextResponse.json({ status: "deleted" });
  } catch (err) {
    return errorResponse(err);
  }
}

export const runtime = "nodejs";
