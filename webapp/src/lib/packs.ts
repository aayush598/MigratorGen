import path from "node:path";
import { readdir, readFile, writeFile, unlink, mkdir } from "node:fs/promises";

export const MIGRATION_PACKS_DIR =
  process.env.MIGRATION_PACKS_DIR || path.resolve(process.cwd(), "..", "migration-packs");

export const USER_PACKS_DIR = process.env.USER_PACKS_DIR
  ? path.resolve(process.env.USER_PACKS_DIR)
  : path.resolve(process.cwd(), "data", "user-packs");

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

export interface UserPackRecord extends PackFile {
  name?: string;
  id: string;
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
  let files: string[] = [];
  try {
    await mkdir(USER_PACKS_DIR, { recursive: true });
    files = (await readdir(USER_PACKS_DIR)).filter((f) => f.endsWith(".json"));
  } catch {
    return [];
  }

  const packs = [];
  for (const file of files) {
    try {
      const content = await readFile(path.join(USER_PACKS_DIR, file), "utf-8");
      const data = JSON.parse(content) as UserPackRecord;
      const packId = file.replace(".json", "");
      const versions = data.versions ?? [];
      packs.push({
        id: packId,
        name: data.name ?? data.library ?? packId,
        description: data.description ?? "",
        library: data.library ?? packId,
        version_count: versions.length,
        rule_count: versions.reduce((sum, v) => sum + (v.rules?.length ?? 0), 0),
        is_published: data.is_published ?? false,
        created_at: data.created_at ?? "",
        updated_at: data.updated_at ?? "",
      });
    } catch {
      continue;
    }
  }
  return packs;
}

export async function getUserPacksDir(): Promise<string> {
  await mkdir(USER_PACKS_DIR, { recursive: true });
  return USER_PACKS_DIR;
}
