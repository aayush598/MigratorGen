import { NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { randomUUID } from "node:crypto";
import { getDb } from "@/lib/db";
import { userPacks } from "@/lib/db-schema";
import { getUserPackById } from "@/lib/packs";
import { requireSession, errorResponse } from "@/lib/api-helpers";

interface RouteContext {
  params: { id: string; version: string };
}

export async function POST(request: Request, context: RouteContext) {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    const { id: packId, version } = context.params;
    const existing = await getUserPackById(packId);
    if (!existing) return NextResponse.json({ error: "Pack not found" }, { status: 404 });

    const body = (await request.json()) as Record<string, unknown>;
    const versions = ((existing.versions as Record<string, unknown>[]) ?? []).map((v) => ({ ...v }));
    let target = versions.find((v) => v.version === version);

    if (!target) {
      target = { version, release_date: null, notes: null, rules: [] };
      versions.push(target);
    }

    const ruleId =
      (body.id as string) || `${packId.slice(0, 4)}-${versions.length}-${randomUUID().slice(0, 4)}`;
    const ruleData = { ...body, id: ruleId, version_introduced: version };
    if (!Array.isArray(target.rules)) target.rules = [];
    (target.rules as unknown[]).push(ruleData);

    const db = getDb();
    await db
      .update(userPacks)
      .set({ versions, updatedAt: new Date().toISOString() })
      .where(eq(userPacks.id, packId));

    return NextResponse.json({ status: "created", rule_id: ruleId });
  } catch (err) {
    return errorResponse(err);
  }
}

export const runtime = "nodejs";
