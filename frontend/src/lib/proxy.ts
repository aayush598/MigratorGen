import { auth } from "@/lib/auth";
import { headers } from "next/headers";

const PYTHON_API = process.env.PYTHON_API_URL || "http://localhost:8000";
const SERVICE_KEY = process.env.SERVICE_KEY || "dev-service-key-change-in-production";

export async function proxyRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const session = await auth.api.getSession({ headers: await headers() });

  const headersMap = new Headers(options.headers);
  headersMap.set("Content-Type", "application/json");
  headersMap.set("X-Service-Key", SERVICE_KEY);

  if (session) {
    headersMap.set("X-User-ID", session.user.id);
    headersMap.set("X-Tenant-ID", session.session.userId);
    headersMap.set("X-User-Role", "owner");
  }

  const res = await fetch(`${PYTHON_API}${path}`, {
    ...options,
    headers: headersMap,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.title || `HTTP ${res.status}`);
  }

  return res.json();
}
