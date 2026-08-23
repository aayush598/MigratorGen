#!/usr/bin/env node

/**
 * Prebuild script: copies engine files from sdk/python into webapp/python/engine/
 *
 * This ensures the single source of truth is sdk/python/src/migrator_gen/core/
 * while keeping the webapp self-contained for Vercel deployment (which only
 * has access to the webapp/ directory).
 *
 * Usage: node scripts/sync-engine.mjs
 * Called automatically by "prebuild" in package.json
 */

import { readdir, readFile, writeFile, mkdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.resolve(__dirname, "..", "..", "sdk", "python", "src", "migrator_gen", "core");
const DST = path.resolve(__dirname, "..", "python", "engine");

async function sync() {
  let files;
  try {
    files = (await readdir(SRC)).filter((f) => f.endsWith(".py"));
  } catch (err) {
    console.error(`[sync-engine] Cannot read SDK source at ${SRC}`);
    console.error(`  ${err.message}`);
    console.error("  Falling back to existing engine files in webapp/python/engine/");
    process.exit(0);
  }

  if (files.length === 0) {
    console.error(`[sync-engine] No .py files found in ${SRC}`);
    process.exit(1);
  }

  // Clean destination
  await rm(DST, { recursive: true, force: true });
  await mkdir(DST, { recursive: true });

  let count = 0;
  for (const file of files) {
    const content = await readFile(path.join(SRC, file), "utf-8");
    await writeFile(path.join(DST, file), content, "utf-8");
    count++;
  }

  console.log(`[sync-engine] Copied ${count} engine files from sdk/python → webapp/python/engine/`);
}

sync().catch((err) => {
  console.error("[sync-engine] Fatal:", err);
  process.exit(1);
});
