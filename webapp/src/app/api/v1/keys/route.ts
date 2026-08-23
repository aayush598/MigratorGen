import { createHash, randomBytes } from "node:crypto";
import { NextResponse } from "next/server";
import { eq, and } from "drizzle-orm";
import { getDb } from "@/lib/db";
import { apiKey } from "@/lib/db-schema";
import { requireSession, errorResponse } from "@/lib/api-helpers";

function generateApiKey(): { raw: string; hash: string; prefix: string } {
  const raw = `mgk_${randomBytes(24).toString("hex")}`;
  const hash = createHash("sha256").update(raw).digest("hex");
  return { raw, hash, prefix: raw.slice(0, 12) };
}

export async function GET() {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    const db = getDb();
    const keys = await db
      .select()
      .from(apiKey)
      .where(and(eq(apiKey.userId, auth.session.userId), eq(apiKey.isActive, true)));

    return NextResponse.json(
      keys.map((k) => ({
        id: k.id,
        name: k.name,
        key_prefix: k.keyPrefix,
        scopes: k.scopes,
        created_at: k.createdAt.toISOString(),
        is_active: k.isActive,
      })),
    );
  } catch (err) {
    return errorResponse(err);
  }
}

export async function POST(request: Request) {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    const body = (await request.json()) as { name?: string; scopes?: string[] };
    if (!body.name) {
      return NextResponse.json({ error: "name is required" }, { status: 422 });
    }

    const { raw, hash, prefix } = generateApiKey();
    const id = `key_${randomBytes(6).toString("hex")}`;

    const db = getDb();
    await db.insert(apiKey).values({
      id,
      userId: auth.session.userId,
      name: body.name,
      keyHash: hash,
      keyPrefix: prefix,
      scopes: body.scopes ?? ["migrate", "read"],
      isActive: true,
    });

    return NextResponse.json({
      id,
      name: body.name,
      key: raw,
      key_prefix: prefix,
      scopes: body.scopes ?? ["migrate", "read"],
      created_at: new Date().toISOString(),
      is_active: true,
    });
  } catch (err) {
    return errorResponse(err);
  }
}

export async function DELETE(request: Request) {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    const url = new URL(request.url);
    const keyId = url.searchParams.get("keyId");
    if (!keyId) {
      return NextResponse.json({ error: "Missing keyId" }, { status: 400 });
    }

    const db = getDb();
    const deleted = await db
      .update(apiKey)
      .set({ isActive: false })
      .where(and(eq(apiKey.id, keyId), eq(apiKey.userId, auth.session.userId)))
      .returning({ id: apiKey.id });

    if (deleted.length === 0) {
      return NextResponse.json({ error: "API key not found" }, { status: 404 });
    }
    return NextResponse.json({ status: "deleted" });
  } catch (err) {
    return errorResponse(err);
  }
}

export const runtime = "nodejs";
