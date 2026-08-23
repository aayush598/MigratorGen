"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, CheckCircle2, ChevronDown } from "lucide-react";
import { client } from "@/lib/api-client";
import type { Rule } from "@/schemas";
import { Card, Badge, EmptyState } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface FlatRule extends Rule {
  library: string;
}

const CT_LABELS: Record<string, string> = {
  rename_import: "Rename import",
  rename_function: "Rename function",
  rename_class: "Rename class",
  rename_attribute: "Rename attribute",
  add_argument: "Add argument",
  remove_argument: "Remove argument",
  move_to_module: "Move to module",
  deprecate_function: "Deprecate function",
};

export default function RulesPage() {
  const [rulesByLib, setRulesByLib] = useState<Record<string, Rule[]>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    client.current.libraries
      .list()
      .then(async (libs) => {
        const result: Record<string, Rule[]> = {};
        for (const [name, lib] of Object.entries(libs)) {
          if (lib.versions) {
            result[name] = lib.versions.flatMap((v) => (v.rules ?? []) as unknown as Rule[]);
            continue;
          }
          try {
            const detail = await client.current.libraries.get(name);
            result[name] = (detail.versions ?? []).flatMap((v) => v.rules ?? []);
          } catch {
            continue;
          }
        }
        if (!cancelled) setRulesByLib(result);
      })
      .catch(() => {})
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const totalRules = Object.values(rulesByLib).reduce((sum, rules) => sum + rules.length, 0);

  const filtered = useMemo<FlatRule[]>(
    () =>
      Object.entries(rulesByLib).flatMap(([lib, rules]) =>
        rules.map((r) => ({ ...r, library: lib })),
      ).filter(
        (r) =>
          !search ||
          r.description?.toLowerCase().includes(search.toLowerCase()) ||
          r.id.toLowerCase().includes(search.toLowerCase()) ||
          r.old_name?.toLowerCase().includes(search.toLowerCase()) ||
          r.new_name?.toLowerCase().includes(search.toLowerCase()),
      ),
    [rulesByLib, search],
  );

  return (
    <div className="animate-fade-up">
      <div className="mb-8">
        <h1 className="text-[28px] font-bold tracking-tight text-slate-900">Migration rules</h1>
        <p className="mt-1 text-sm text-slate-500">
          {loading ? (
            <span className="skeleton inline-block h-4 w-48" />
          ) : (
            <>
              {totalRules} rules across {Object.keys(rulesByLib).length} libraries
            </>
          )}
        </p>
      </div>

      <div className="relative mb-8 max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, description, or ID…"
          className="pl-9"
        />
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="skeleton h-16 rounded-xl" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState icon={<CheckCircle2 className="h-5 w-5" />} title="No rules found" description={search ? "Try a different search term." : "No libraries with rules yet."} />
      ) : (
        <div className="space-y-2">
          {filtered.map((rule) => {
            const key = `${rule.library}-${rule.id}`;
            const isOpen = expanded === key;
            return (
              <Card key={key} className={cn("overflow-hidden transition-colors", isOpen && "border-slate-300")}>
                <button onClick={() => setExpanded(isOpen ? null : key)} className="flex w-full items-center gap-4 p-4 text-left hover:bg-slate-50/60">
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex flex-wrap items-center gap-2">
                      <Badge>{CT_LABELS[rule.change_type] || rule.change_type}</Badge>
                      <span className="font-mono text-[11px] text-slate-400">{rule.library}</span>
                      <Badge tone={rule.safety === "safe" ? "success" : rule.safety === "review_required" ? "warning" : "danger"}>
                        {(rule.safety ?? "").replace("_", " ") || "safe"}
                      </Badge>
                    </div>
                    <p className="truncate text-[13px] text-slate-700">{rule.description}</p>
                    {(rule.old_name || rule.new_name) && (
                      <p className="mt-0.5 font-mono text-xs text-slate-400">
                        {rule.old_name || "—"} → {rule.new_name || "—"}
                      </p>
                    )}
                  </div>
                  <ChevronDown className={cn("h-4 w-4 shrink-0 text-slate-400 transition-transform", isOpen && "rotate-180")} />
                </button>
                {isOpen && (
                  <div className="animate-fade-in border-t border-slate-100 px-4 pb-4 pt-3">
                    <div className="grid grid-cols-2 gap-4 text-xs sm:grid-cols-4">
                      <div>
                        <span className="mb-0.5 block font-medium text-slate-400">ID</span>
                        <span className="font-mono text-slate-700">{rule.id}</span>
                      </div>
                      <div>
                        <span className="mb-0.5 block font-medium text-slate-400">Type</span>
                        <span className="text-slate-700">{rule.change_type}</span>
                      </div>
                      <div>
                        <span className="mb-0.5 block font-medium text-slate-400">Library</span>
                        <span className="text-slate-700">{rule.library}</span>
                      </div>
                      <div>
                        <span className="mb-0.5 block font-medium text-slate-400">Tags</span>
                        <span className="text-slate-700">{rule.tags.join(", ") || "—"}</span>
                      </div>
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
