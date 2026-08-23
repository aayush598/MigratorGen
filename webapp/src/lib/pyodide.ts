import { readFile } from "node:fs/promises";
import path from "node:path";
import type { PyodideInterface } from "pyodide";

export interface RuleResult {
  rule_id: string;
  success: boolean;
  confidence: number;
  changes_made: string[];
  errors: string[];
}

export interface PreviewResult {
  original_code: string;
  transformed_code: string;
  diff: string;
  changes: string[];
  change_count: number;
  average_confidence: number;
  rule_results: RuleResult[];
  duration_ms: number;
  target_version: string;
}

export interface MigrateResult extends Omit<PreviewResult, "diff"> {
  rules_applied: string[];
  was_modified: boolean;
  errors: string[];
}

export interface ValidationIssue {
  rule_id: string;
  message: string;
  severity: string;
}

export interface ValidationReport {
  valid: boolean;
  error_count: number;
  warning_count: number;
  info_count: number;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
  info: ValidationIssue[];
}

export class EngineError extends Error {
  readonly detail: unknown;

  constructor(message: string, detail?: unknown) {
    super(message);
    this.name = "EngineError";
    this.detail = detail;
  }
}

type PyodideModule = { loadPyodide: (opts?: Record<string, unknown>) => Promise<PyodideInterface> };

let enginePromise: Promise<PyodideInterface> | null = null;

const SITE_PACKAGES = "/lib/python3.13/site-packages";
const ENGINE_VERSION = "1.0.1";

async function writeWebApiFile(pyodide: PyodideInterface): Promise<void> {
  const webApiPath = path.resolve(process.cwd(), "python", "web_api.py");
  const content = await readFile(webApiPath, "utf-8");
  pyodide.FS.writeFile(path.posix.join(SITE_PACKAGES, "web_api.py"), content);
}

async function createEngine(): Promise<PyodideInterface> {
  const { loadPyodide } = (await import("pyodide")) as PyodideModule;
  const pyodide = await loadPyodide();

  try {
    await pyodide.loadPackage("micropip");
    const micropip = pyodide.pyimport("micropip");
    await micropip.install(["libcst", "pydantic", `migrator-gen==${ENGINE_VERSION}`]);
  } catch (err) {
    throw new EngineError("Failed to install Python dependencies", err);
  }

  try {
    await writeWebApiFile(pyodide);
  } catch (err) {
    throw new EngineError("Failed to load web_api.py", err);
  }

  pyodide.runPython(`
import sys, json
sys.path.insert(0, "${SITE_PACKAGES}")
import web_api
`);

  return pyodide;
}

export function getEngine(): Promise<PyodideInterface> {
  if (!enginePromise) {
    enginePromise = createEngine().catch((err) => {
      enginePromise = null;
      throw err;
    });
  }
  return enginePromise;
}

async function callApi<T>(fn: string, args: Record<string, string>): Promise<T> {
  const pyodide = await getEngine();
  const placeholders: string[] = [];
  let script = "";
  Object.entries(args).forEach(([key, value], i) => {
    const placeholder = `__arg${i}`;
    pyodide.globals.set(placeholder, value);
    placeholders.push(placeholder);
    script += `${placeholder} = ${placeholder}\n`;
  });
  const kwargs = Object.keys(args)
    .map((k, i) => `${k}=__arg${i}`)
    .join(", ");
  try {
    const raw = pyodide.runPython(`${script}web_api.${fn}(${kwargs})`);
    return JSON.parse(raw) as T;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    const lines = message
      .trim()
      .split("\n")
      .filter(Boolean)
      .filter((line) => !/^\s*For further information visit/i.test(line));
    const lastLine = lines.pop() ?? "Unknown engine error";
    throw new EngineError(lastLine, err);
  } finally {
    for (const placeholder of placeholders) {
      pyodide.globals.delete(placeholder);
    }
  }
}

export function previewCode(
  sourceCode: string,
  rules: unknown[],
  targetVersion: string,
): Promise<PreviewResult> {
  return callApi("preview", {
    source_code: sourceCode,
    rules_json: JSON.stringify(rules),
    target_version: targetVersion,
  });
}

export function migrateCode(
  sourceCode: string,
  rules: unknown[],
  targetVersion: string,
): Promise<MigrateResult> {
  return callApi("migrate", {
    source_code: sourceCode,
    rules_json: JSON.stringify(rules),
    target_version: targetVersion,
  });
}

export function validateRules(content: Record<string, unknown>): Promise<ValidationReport> {
  return callApi("validate", { rules_content_json: JSON.stringify(content) });
}

export interface ResolvedPathResult {
  source_version: string;
  target_version: string;
  is_upgrade: boolean;
  steps: { source: string; target: string; rule_count: number }[];
  rule_count: number;
}

export function resolvePath(
  sourceVersion: string,
  targetVersion: string,
  changelogJson: string,
): Promise<ResolvedPathResult> {
  return callApi("resolve_path", {
    source_version: sourceVersion,
    target_version: targetVersion,
    changelog_json: changelogJson,
  });
}

export async function engineHealth(): Promise<{ status: string; engine: string; version: string }> {
  const started = Date.now();
  await getEngine();
  return { status: "healthy", engine: "pyodide", version: `init-${Date.now() - started}ms` };
}
