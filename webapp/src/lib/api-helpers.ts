import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

export async function requireSession(): Promise<
  { ok: true; session: { userId: string; tenantId: string } } | { ok: false; response: NextResponse }
> {
  const { userId } = await auth();
  if (!userId) {
    return {
      ok: false,
      response: NextResponse.json({ error: "Unauthorized" }, { status: 401 }),
    };
  }
  return {
    ok: true,
    session: { userId, tenantId: userId },
  };
}

export async function getSessionOptional(): Promise<{ userId: string; tenantId: string } | null> {
  const { userId } = await auth();
  if (!userId) return null;
  return { userId, tenantId: userId };
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
