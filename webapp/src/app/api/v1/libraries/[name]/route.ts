import { NextResponse } from "next/server";
import { getBuiltinPack, listUserPacks } from "@/lib/packs";

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
      const { readFile } = await import("node:fs/promises");
      const { USER_PACKS_DIR } = await import("@/lib/packs");
      const data = JSON.parse(
        await readFile(`${USER_PACKS_DIR}/${pack.id}.json`, "utf-8"),
      );
      return NextResponse.json({
        name: pack.library,
        rule_count: pack.rule_count,
        source: "user",
        description: pack.description,
        versions: data.versions ?? [],
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
