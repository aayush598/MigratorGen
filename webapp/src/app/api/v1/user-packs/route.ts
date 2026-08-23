import { NextResponse } from "next/server";
import { readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { USER_PACKS_DIR } from "@/lib/packs";
import { requireSession, errorResponse } from "@/lib/api-helpers";

export async function GET() {
  try {
    const auth = await requireSession();
    if (!auth.ok) return auth.response;

    await mkdirSafe();
    const files = (await readdir(USER_PACKS_DIR)).filter((f) => f.endsWith(".json"));
    const packs = [];
    for (const file of files) {
      try {
        const data = JSON.parse(await readFile(path.join(USER_PACKS_DIR, file), "utf-8")) as Record<string, unknown>;
        const packId = file.replace(".json", "");
        const versions = (data.versions as unknown[]) ?? [];
        packs.push({
          id: packId,
          name: (data.name as string) ?? packId,
          description: (data.description as string) ?? "",
          library: (data.library as string) ?? packId,
          version_count: versions.length,
          rule_count: versions.reduce(
            (sum: number, v) => sum + (((v as Record<string, unknown>).rules as unknown[])?.length ?? 0),
            0,
          ),
          is_published: (data.is_published as boolean) ?? false,
          created_at: (data.created_at as string) ?? "",
          updated_at: (data.updated_at as string) ?? "",
        });
      } catch {
        continue;
      }
    }
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

    await mkdirSafe();
    const packId = randomUUID().slice(0, 8);
    const now = new Date().toISOString();
    await writeFile(
      path.join(USER_PACKS_DIR, `${packId}.json`),
      JSON.stringify(
        {
          library: body.library,
          name: body.name,
          description: body.description ?? "",
          schema_version: "1.0",
          is_published: false,
          created_at: now,
          updated_at: now,
          versions: body.versions ?? [],
        },
        null,
        2,
      ),
      "utf-8",
    );

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

async function mkdirSafe() {
  const { mkdir } = await import("node:fs/promises");
  await mkdir(USER_PACKS_DIR, { recursive: true });
}

export const runtime = "nodejs";
