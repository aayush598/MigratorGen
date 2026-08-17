import { NextResponse } from "next/server";
import { proxyRequest } from "@/lib/proxy";

export async function GET() {
  const data = await proxyRequest("/api/v1/libraries");
  return NextResponse.json(data);
}
