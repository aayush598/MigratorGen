import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { proxyRequest } from "@/lib/proxy";

export async function POST(request: Request) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const data = await proxyRequest("/api/v1/preview", {
    method: "POST",
    body: JSON.stringify(body),
  });

  return NextResponse.json(data);
}
