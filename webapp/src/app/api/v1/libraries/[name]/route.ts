import { NextResponse } from "next/server";
import { getBuiltinPack, listUserPacks, getUserPackById } from "@/lib/packs";

interface RouteContext {
  params: { name: string };
}

export async function GET(_request: Request, context: RouteContext) {
  try {
    const { name } = context.params;
    const decodedName = decodeURIComponent(name);

    const builtin = await getBuiltinPack(decodedName);
    if (builtin) {
      return NextResponse.json({
        name: builtin.library,
        rule_count: builtin.versions?.reduce((sum, v) => sum + (v.rules?.length ?? 0), 0) ?? 0,
        source: "builtin",
        description: builtin.description ?? "",
        versions: builtin.versions ?? [],
      });
    }

    const userPacks = await listUserPacks();
    const pack = userPacks.find((p) => p.library === decodedName || p.id === decodedName);
    if (pack) {
      const data = await getUserPackById(pack.id);
      return NextResponse.json({
        name: pack.library,
        rule_count: pack.rule_count,
        source: "user",
        description: pack.description,
        versions: (data?.versions as unknown[]) ?? [],
      });
    }

    return NextResponse.json({ error: `Library '${decodedName}' not found` }, { status: 404 });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Internal server error" },
      { status: 500 },
    );
  }
}

export const runtime = "nodejs";
