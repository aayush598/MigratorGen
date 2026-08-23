import { NextResponse } from "next/server";
import { listBuiltinPacks, listUserPacks } from "@/lib/packs";

export async function GET() {
  try {
    const [builtin, userPacks] = await Promise.all([
      listBuiltinPacks(),
      listUserPacks(),
    ]);

    for (const pack of userPacks) {
      builtin[pack.library] = {
        name: pack.library,
        rule_count: pack.rule_count,
        source: "user",
        description: pack.description,
        versions: undefined,
      };
    }

    return NextResponse.json({ libraries: builtin });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Internal server error" },
      { status: 500 },
    );
  }
}

export const runtime = "nodejs";
