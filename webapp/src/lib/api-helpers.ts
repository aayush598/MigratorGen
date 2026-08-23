import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { headers } from "next/headers";

export type SessionContext = {
  userId: string;
  tenantId: string;
} | null;

export async function requireSession(): Promise<
  { ok: true; session: { userId: string; tenantId: string } } | { ok: false; response: NextResponse }
> {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return {
      ok: false,
      response: NextResponse.json({ error: "Unauthorized" }, { status: 401 }),
    };
  }
  return {
    ok: true,
    session: { userId: session.user.id, tenantId: session.session.userId },
  };
}

export async function getSessionOptional(): Promise<SessionContext> {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) return null;
  return { userId: session.user.id, tenantId: session.session.userId };
}

export function errorResponse(err: unknown): NextResponse {
  const message = err instanceof Error ? err.message : "Internal server error";
  const status =
    message.includes("not found") ? 404
    : message.includes("Unauthorized") || message.includes("Authentication") ? 401
    : message.includes("Invalid") || message.includes("validation") ? 422
    : 500;
  return NextResponse.json({ error: message }, { status });
}
