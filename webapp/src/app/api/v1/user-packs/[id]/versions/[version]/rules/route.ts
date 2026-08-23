import { NextResponse } from "next/server";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { USER_PACKS_DIR } from "@/lib/packs";
import { requireSession, errorResponse } from "@/lib/api-helpers";

interface RouteContext {
  params: { id: string; version: string };
}

export async function POST(request: Request, context: RouteContext) {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    const { id: packId, version } = context.params;
    const filePath = path.join(USER_PACKS_DIR, `${packId}.json`);
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(await readFile(filePath, "utf-8")) as Record<string, unknown>;
    } catch {
      return NextResponse.json({ error: "Pack not found" }, { status: 404 });
    }

    const body = (await request.json()) as Record<string, unknown>;
    const versions = ((data.versions as Record<string, unknown>[]) ?? []).map((v) => v);
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

    data.versions = versions;
    data.updated_at = new Date().toISOString();
    await writeFile(filePath, JSON.stringify(data, null, 2), "utf-8");

    return NextResponse.json({ status: "created", rule_id: ruleId });
  } catch (err) {
    return errorResponse(err);
  }
}

export const runtime = "nodejs";
