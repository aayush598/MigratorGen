import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { proxyRequest } from "@/lib/proxy";

export async function GET() {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const data = await proxyRequest("/api/v1/keys");
  return NextResponse.json(data);
}

export async function POST(request: Request) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const data = await proxyRequest("/api/v1/keys", {
    method: "POST",
    body: JSON.stringify(body),
  });

  return NextResponse.json(data);
}

export async function DELETE(request: Request) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const url = new URL(request.url);
  const keyId = url.searchParams.get("keyId");
  if (!keyId) {
    return NextResponse.json({ error: "Missing keyId" }, { status: 400 });
  }

  const data = await proxyRequest(`/api/v1/keys/${keyId}`, {
    method: "DELETE",
  });

  return NextResponse.json(data);
}
