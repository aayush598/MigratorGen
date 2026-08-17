import { NextResponse } from "next/server";
import { proxyRequest } from "@/lib/proxy";

export async function GET(
  request: Request,
  { params }: { params: { name: string } }
) {
  const data = await proxyRequest(`/api/v1/libraries/${params.name}`);
  return NextResponse.json(data);
}
