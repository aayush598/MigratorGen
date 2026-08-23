import {
  RuleSchema, MigrateResponseSchema, DiffPreviewSchema,
  ValidationReportSchema, ResolvedPathSchema, LibraryInfoSchema,
  ApiKeySchema, UserPackSummarySchema, UserPackDetailSchema,
  HealthStatusSchema, MigrationFileSchema,
  type MigrateResponse, type DiffPreview, type ValidationReport,
  type ResolvedPath, type LibraryInfo, type ApiKey,
  type UserPackSummary, type UserPackDetail, type HealthStatus,
  type MigrationFile,
} from "@/schemas";

// ─── Errors ───────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  readonly code: string;
  readonly status?: number;
  readonly details?: unknown;
  constructor(message: string, opts: { code?: string; status?: number; details?: unknown } = {}) {
    super(message);
    this.name = "ApiError";
    this.code = opts.code ?? "API_ERROR";
    this.status = opts.status;
    this.details = opts.details;
  }
}

function mapStatusToError(status: number, message: string, details?: unknown): ApiError {
  const code =
    status === 401 ? "AUTHENTICATION_ERROR" :
    status === 404 ? "NOT_FOUND" :
    status === 409 ? "CONFLICT" :
    status === 422 ? "VALIDATION_ERROR" :
    status === 429 ? "RATE_LIMIT" :
    status >= 500 ? "ENGINE_ERROR" : "API_ERROR";
  return new ApiError(message, { code, status, details });
}

// ─── HTTP ─────────────────────────────────────────────────────────────────────

const RETRYABLE = new Set([502, 503, 504]);

async function http<T>(
  baseUrl: string,
  path: string,
  opts: { method?: string; body?: unknown; query?: Record<string, string | undefined>; timeoutMs?: number; maxRetries?: number } = {},
): Promise<T> {
  const url = new URL(`${baseUrl}${path}`, resolveBase(baseUrl));
  for (const [k, v] of Object.entries(opts.query ?? {})) {
    if (v !== undefined) url.searchParams.set(k, v);
  }
  const timeoutMs = opts.timeoutMs ?? 30_000;
  const maxRetries = opts.maxRetries ?? 2;
  let attempt = 0;
  let lastError: Error = new ApiError("Request never executed", { code: "ENGINE_ERROR" });

  while (attempt <= maxRetries) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const res = await fetch(url.toString(), {
        method: opts.method ?? "GET",
        headers: { "Content-Type": "application/json" },
        body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
        credentials: "include",
        signal: ctrl.signal,
      });
      const text = await res.text();
      const parsed = safeParse(text);
      if (!res.ok) {
        const msg =
          (isObj(parsed) && typeof parsed.detail === "string" && parsed.detail) ||
          (isObj(parsed) && typeof parsed.error === "string" && parsed.error) ||
          `HTTP ${res.status}`;
        if (RETRYABLE.has(res.status) && attempt < maxRetries) {
          lastError = mapStatusToError(res.status, msg, parsed);
          attempt++;
          await sleep(Math.min(100 * 2 ** (attempt - 1), 2000));
          continue;
        }
        throw mapStatusToError(res.status, msg, parsed);
      }
      return (parsed ?? {}) as T;
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        throw new ApiError(`Request timed out after ${timeoutMs}ms`, { code: "TIMEOUT" });
      }
      if (err instanceof ApiError && err.code !== "TIMEOUT" && attempt < maxRetries) {
        lastError = err;
        attempt++;
        await sleep(Math.min(100 * 2 ** (attempt - 1), 2000));
        continue;
      }
      throw err;
    } finally {
      clearTimeout(timer);
    }
  }
  throw lastError;
}

function resolveBase(b: string): string {
  if (b.startsWith("http")) return b;
  if (typeof window !== "undefined") return window.location.origin;
  return "http://localhost:3000";
}
function safeParse(t: string): unknown {
  if (!t) return {};
  try { return JSON.parse(t); } catch { return { detail: t }; }
}
function isObj(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null;
}
async function sleep(ms: number) {
  await new Promise((r) => setTimeout(r, ms));
}

// ─── Client ───────────────────────────────────────────────────────────────────

export interface MigrateOptions {
  sourceVersion?: string;
  targetVersion?: string;
  dryRun?: boolean;
}

export class MigratorGenClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly maxRetries: number;

  constructor(opts: { baseUrl?: string; timeoutMs?: number; maxRetries?: number } = {}) {
    this.baseUrl = (opts.baseUrl ?? "/api/v1").replace(/\/+$/, "");
    this.timeoutMs = opts.timeoutMs ?? 30_000;
    this.maxRetries = opts.maxRetries ?? 2;
  }

  private req<T>(path: string, o?: { method?: string; body?: unknown; query?: Record<string, string | undefined> }) {
    return http<T>(this.baseUrl, path, { ...o, timeoutMs: this.timeoutMs, maxRetries: this.maxRetries });
  }

  async health() {
    return HealthStatusSchema.parse(await this.req<unknown>("/health"));
  }

  async migrate(sourceCode: string, rules: unknown[], options: MigrateOptions = {}): Promise<MigrateResponse> {
    const validated = rules.map((r, i) => {
      const res = RuleSchema.safeParse(r);
      if (!res.success) throw new ApiError(`Invalid rule at index ${i}`, { code: "VALIDATION_ERROR", status: 422 });
      return res.data;
    });
    return MigrateResponseSchema.parse(await this.req<unknown>("/migrate", {
      method: "POST",
      body: { source_code: sourceCode, rules: validated, source_version: options.sourceVersion ?? "", target_version: options.targetVersion ?? "", dry_run: options.dryRun ?? false },
    }));
  }

  async preview(sourceCode: string, rules: unknown[], options: MigrateOptions = {}): Promise<DiffPreview> {
    return DiffPreviewSchema.parse(await this.req<unknown>("/preview", {
      method: "POST",
      body: { source_code: sourceCode, rules, source_version: options.sourceVersion ?? "", target_version: options.targetVersion ?? "" },
    }));
  }

  async validateRules(rulesPath: string): Promise<ValidationReport> {
    return ValidationReportSchema.parse(await this.req<unknown>("/validate", { method: "POST", body: { rules_path: rulesPath } }));
  }

  async resolvePath(sourceVersion: string, targetVersion: string, libraryName: string): Promise<ResolvedPath> {
    return ResolvedPathSchema.parse(await this.req<unknown>("/resolve-path", {
      method: "POST",
      body: { source_version: sourceVersion, target_version: targetVersion, library_name: libraryName },
    }));
  }

  readonly libraries = {
    list: async (): Promise<Record<string, LibraryInfo>> => {
      const raw = await this.req<{ libraries: unknown }>("/libraries");
      const record = (raw?.libraries ?? {}) as Record<string, unknown>;
      const out: Record<string, LibraryInfo> = {};
      for (const [name, info] of Object.entries(record)) {
        out[name] = LibraryInfoSchema.parse({ name, ...(typeof info === "object" && info !== null ? info : {}) });
      }
      return out;
    },
    get: async (name: string): Promise<LibraryInfo> => {
      const raw = await this.req<unknown>(`/libraries/${encodeURIComponent(name)}`);
      return LibraryInfoSchema.parse({ name, ...(typeof raw === "object" && raw !== null ? raw : {}) });
    },
  };

  readonly packs = {
    list: async (): Promise<UserPackSummary[]> => {
      const raw = await this.req<{ packs?: unknown[] }>("/user-packs");
      return (raw.packs ?? []).map((p) => UserPackSummarySchema.parse(p));
    },
    get: async (id: string): Promise<UserPackDetail> => {
      const raw = await this.req<unknown>(`/user-packs/${encodeURIComponent(id)}`);
      return UserPackDetailSchema.parse(raw);
    },
    create: async (data: { name: string; description?: string; library: string; versions?: unknown[] }): Promise<UserPackSummary> => {
      const raw = (await this.req<Record<string, unknown>>("/user-packs", { method: "POST", body: data })) as { id?: string };
      return UserPackSummarySchema.parse({ id: raw?.id ?? "", name: data.name, library: data.library });
    },
    update: async (id: string, data: { name?: string; description?: string; versions?: unknown[] }): Promise<void> => {
      await this.req(`/user-packs/${encodeURIComponent(id)}`, { method: "PUT", body: data });
    },
    delete: async (id: string): Promise<void> => {
      await this.req(`/user-packs/${encodeURIComponent(id)}`, { method: "DELETE" });
    },
    publish: async (id: string): Promise<void> => {
      await this.req(`/user-packs/${encodeURIComponent(id)}/publish`, { method: "POST" });
    },
    unpublish: async (id: string): Promise<void> => {
      await this.req(`/user-packs/${encodeURIComponent(id)}/publish`, { method: "POST" });
    },
    addRule: async (packId: string, version: string, rule: Record<string, unknown>): Promise<string> => {
      const raw = await this.req<{ rule_id?: string }>(
        `/user-packs/${encodeURIComponent(packId)}/versions/${encodeURIComponent(version)}/rules`,
        { method: "POST", body: rule },
      );
      return raw.rule_id ?? "";
    },
  };

  readonly keys = {
    list: async (): Promise<ApiKey[]> => {
      const raw = await this.req<unknown[]>("/keys");
      return (Array.isArray(raw) ? raw : []).map((k) => ApiKeySchema.parse(k));
    },
    create: async (name: string, scopes: string[] = ["migrate", "read"]): Promise<ApiKey> => {
      const raw = await this.req<unknown>("/keys", { method: "POST", body: { name, scopes } });
      return ApiKeySchema.parse(raw);
    },
    delete: async (keyId: string): Promise<void> => {
      await this.req("/keys", { method: "DELETE", query: { keyId } });
    },
  };

  parseMigrationFile(content: string): MigrationFile {
    return MigrationFileSchema.parse(JSON.parse(content));
  }
}

// ─── Singleton ────────────────────────────────────────────────────────────────

let instance: MigratorGenClient | null = null;

export function getClient(): MigratorGenClient {
  if (!instance) instance = new MigratorGenClient({ baseUrl: "/api/v1", timeoutMs: 60_000, maxRetries: 1 });
  return instance;
}

export const client = {
  get current() { return getClient(); },
};
