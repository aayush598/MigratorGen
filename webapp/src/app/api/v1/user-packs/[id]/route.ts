import { NextResponse } from "next/server";
import { readFile, writeFile, unlink } from "node:fs/promises";
import path from "node:path";
import { USER_PACKS_DIR } from "@/lib/packs";
import { requireSession, errorResponse } from "@/lib/api-helpers";

interface RouteContext {
  params: { id: string };
}

async function readPack(packId: string): Promise<Record<string, unknown> | null> {
  try {
    const content = await readFile(path.join(USER_PACKS_DIR, `${packId}.json`), "utf-8");
    return JSON.parse(content) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export async function GET(_request: Request, context: RouteContext) {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    const data = await readPack(context.params.id);
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
    const data = await readPack(packId);
    if (!data) return NextResponse.json({ error: "Pack not found" }, { status: 404 });

    const body = (await request.json()) as {
      name?: string;
      description?: string;
      versions?: unknown[];
    };
    if (body.name !== undefined) data.name = body.name;
    if (body.description !== undefined) data.description = body.description;
    if (body.versions !== undefined) data.versions = body.versions;
    data.updated_at = new Date().toISOString();

    await writeFile(path.join(USER_PACKS_DIR, `${packId}.json`), JSON.stringify(data, null, 2), "utf-8");
    return NextResponse.json({ status: "updated", id: packId });
  } catch (err) {
    return errorResponse(err);
  }
}

export async function DELETE(_request: Request, context: RouteContext) {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    try {
      await unlink(path.join(USER_PACKS_DIR, `${context.params.id}.json`));
    } catch {
      return NextResponse.json({ error: "Pack not found" }, { status: 404 });
    }
    return NextResponse.json({ status: "deleted" });
  } catch (err) {
    return errorResponse(err);
  }
}

export const runtime = "nodejs";
