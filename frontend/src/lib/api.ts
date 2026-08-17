const PROXY_BASE = "/api/proxy";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };

  const res = await fetch(`${PROXY_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.error || body.title || `HTTP ${res.status}`);
  }

  return res.json();
}

export const api = {
  migrations: {
    migrate: (sourceCode: string, rules: unknown[], sourceVersion?: string, targetVersion?: string) =>
      request<{
        transformed_code: string;
        changes: string[];
        was_modified: boolean;
        average_confidence: number;
        errors: string[];
      }>("/migrate", {
        method: "POST",
        body: JSON.stringify({
          source_code: sourceCode,
          rules,
          source_version: sourceVersion || "",
          target_version: targetVersion || "",
        }),
      }),

    preview: (sourceCode: string, rules: unknown[], sourceVersion?: string, targetVersion?: string) =>
      request<{
        diff: string;
        changes: string[];
        change_count: number;
        average_confidence: number;
        transformed_code?: string;
      }>("/preview", {
        method: "POST",
        body: JSON.stringify({
          source_code: sourceCode,
          rules,
          source_version: sourceVersion || "",
          target_version: targetVersion || "",
        }),
      }),
  },

  libraries: {
    list: () => request<{ libraries: Record<string, { rule_count: number; source: string; description?: string; versions?: { version: string; rules: unknown[] }[] }> }>("/libraries"),
    get: (name: string) => request<{ name: string; rule_count: number; source: string; versions: { version: string; rules: unknown[] }[] }>(`/libraries/${encodeURIComponent(name)}`),
  },

  keys: {
    list: () =>
      request<{ id: string; name: string; key_prefix: string; scopes: string[]; is_active: boolean }[]>(
        "/keys"
      ),
    create: (name: string, scopes: string[]) =>
      request<{ id: string; key: string; name: string }>("/keys", {
        method: "POST",
        body: JSON.stringify({ name, scopes }),
      }),
    delete: (keyId: string) =>
      request<{ status: string }>(`/keys?keyId=${keyId}`, {
        method: "DELETE",
      }),
  },

  userPacks: {
    list: () =>
      request<{ packs: { id: string; name: string; description: string; library: string; version_count: number; rule_count: number; is_published: boolean }[] }>("/user-packs"),
    create: (data: { name: string; description: string; library: string; versions: unknown[] }) =>
      request<{ id: string; name: string; library: string }>("/user-packs", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    get: (id: string) =>
      request<{ id: string; name: string; description: string; library: string; published: boolean; versions: { version: string; release_date?: string; rules: { id: string; change_type: string; description: string; old_name?: string; new_name?: string; old_module?: string; new_module?: string; function_name?: string; argument_name?: string; safety: string; confidence_hint: string; tags: string[]; version_introduced?: string }[] }[]; version_count: number; rule_count: number; created_at: string }>(`/user-packs/${id}`),
    update: (id: string, data: { name?: string; description?: string; versions?: unknown[] }) =>
      request<{ status: string }>(`/user-packs/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<{ status: string }>(`/user-packs/${id}`, {
        method: "DELETE",
      }),
    publish: (id: string) =>
      request<{ status: string }>(`/user-packs/${id}/publish`, {
        method: "POST",
      }),
    unpublish: (id: string) =>
      request<{ status: string }>(`/user-packs/${id}/publish`, {
        method: "POST",
      }),
    addRule: (packId: string, version: string, rule: Record<string, unknown>) =>
      request<{ rule_id: string }>(`/user-packs/${packId}/versions/${version}/rules`, {
        method: "POST",
        body: JSON.stringify(rule),
      }),
  },

  // Convenience aliases
  preview: (sourceCode: string, rules: unknown[], sourceVersion?: string, targetVersion?: string) =>
    request<{
      diff: string;
      changes: string[];
      change_count: number;
      average_confidence: number;
      transformed_code?: string;
    }>("/preview", {
      method: "POST",
      body: JSON.stringify({
        source_code: sourceCode,
        rules,
        source_version: sourceVersion || "",
        target_version: targetVersion || "",
      }),
    }),

  migrate: (sourceCode: string, rules: unknown[], sourceVersion?: string, targetVersion?: string) =>
    request<{
      transformed_code: string;
      changes: string[];
      was_modified: boolean;
      average_confidence: number;
      errors: string[];
    }>("/migrate", {
      method: "POST",
      body: JSON.stringify({
        source_code: sourceCode,
        rules,
        source_version: sourceVersion || "",
        target_version: targetVersion || "",
      }),
    }),
};
