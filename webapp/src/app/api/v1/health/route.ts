import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    status: "healthy",
    service: "migratorgen-web",
    version: "0.2.0",
    timestamp: new Date().toISOString(),
  });
}

export const runtime = "nodejs";
