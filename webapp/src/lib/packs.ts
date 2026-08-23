import path from "node:path";
import { readdir, readFile } from "node:fs/promises";
import { eq } from "drizzle-orm";
import { getDb } from "./db";
import { userPacks } from "./db-schema";

export const MIGRATION_PACKS_DIR =
  process.env.MIGRATION_PACKS_DIR || path.resolve(process.cwd(), "..", "migration-packs");

export interface PackVersion {
  version: string;
  release_date?: string | null;
  notes?: string | null;
  rules: Record<string, unknown>[];
}

export interface PackFile {
  library: string;
  description?: string;
  schema_version?: string;
  is_published?: boolean;
  created_at?: string;
  updated_at?: string;
  versions: PackVersion[];
}

export async function listBuiltinPacks(): Promise<
  Record<string, { name: string; rule_count: number; source: string; description?: string; versions?: { version: string; rule_count: number }[] }>
> {
  let files: string[] = [];
  try {
    files = (await readdir(MIGRATION_PACKS_DIR)).filter((f) => f.endsWith(".json"));
  } catch {
    return {};
  }

  const out: Record<string, { name: string; rule_count: number; source: string; description?: string; versions?: { version: string; rule_count: number }[] }> = {};
  for (const file of files) {
    try {
      const content = await readFile(path.join(MIGRATION_PACKS_DIR, file), "utf-8");
      const pack = JSON.parse(content) as PackFile;
      const ruleCount = pack.versions?.reduce((sum, v) => sum + (v.rules?.length ?? 0), 0) ?? 0;
      out[pack.library ?? file.replace(".json", "")] = {
        name: pack.library ?? file.replace(".json", ""),
        rule_count: ruleCount,
        source: "builtin",
        description: pack.description,
        versions: pack.versions?.map((v) => ({
          version: v.version,
          rule_count: v.rules?.length ?? 0,
        })),
      };
    } catch {
      continue;
    }
  }
  return out;
}

export async function getBuiltinPack(name: string): Promise<(PackFile & { library: string }) | null> {
  let files: string[] = [];
  try {
    files = (await readdir(MIGRATION_PACKS_DIR)).filter((f) => f.endsWith(".json"));
  } catch {
    return null;
  }
  for (const file of files) {
    try {
      const content = await readFile(path.join(MIGRATION_PACKS_DIR, file), "utf-8");
      const pack = JSON.parse(content) as PackFile;
      if ((pack.library ?? file.replace(".json", "")) === name) {
        return { ...pack, library: pack.library ?? name };
      }
    } catch {
      continue;
    }
  }
  return null;
}

export async function listUserPacks(): Promise<
  { id: string; name: string; description: string; library: string; version_count: number; rule_count: number; is_published: boolean; created_at: string; updated_at: string }[]
> {
  try {
    const db = getDb();
    const rows = await db.select().from(userPacks);
    return rows.map((row) => {
      const versions = (row.versions as PackVersion[]) ?? [];
      return {
        id: row.id,
        name: row.name ?? row.library,
        description: row.description ?? "",
        library: row.library,
        version_count: versions.length,
        rule_count: versions.reduce((sum, v) => sum + (v.rules?.length ?? 0), 0),
        is_published: row.isPublished ?? false,
        created_at: row.createdAt ?? "",
        updated_at: row.updatedAt ?? "",
      };
    });
  } catch {
    return [];
  }
}

export async function getUserPackById(id: string): Promise<Record<string, unknown> | null> {
  try {
    const db = getDb();
    const rows = await db.select().from(userPacks).where(eq(userPacks.id, id)).limit(1);
    if (rows.length === 0) return null;
    const row = rows[0];
    return {
      library: row.library,
      name: row.name,
      description: row.description,
      schema_version: row.schemaVersion,
      is_published: row.isPublished,
      created_at: row.createdAt,
      updated_at: row.updatedAt,
      versions: row.versions,
    };
  } catch {
    return null;
  }
}
