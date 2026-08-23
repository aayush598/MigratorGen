"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Rule {
  id: string;
  change_type: string;
  description: string;
  old_name?: string;
  new_name?: string;
  safety: string;
  confidence_hint: string;
  tags: string[];
}

const CT_LABELS: Record<string, string> = {
  rename_import: "Rename import", rename_function: "Rename function", rename_class: "Rename class",
  rename_attribute: "Rename attribute", add_argument: "Add argument", remove_argument: "Remove argument",
  move_to_module: "Move to module", deprecate_function: "Deprecate function",
};

export default function RulesPage() {
  const [rulesByLib, setRulesByLib] = useState<Record<string, Rule[]>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    api.libraries.list().then(async (libs) => {
      const result: Record<string, Rule[]> = {};
      for (const [name] of Object.entries(libs.libraries)) {
        try {
          const detail = await api.libraries.get(name);
          for (const v of detail.versions || []) {
            for (const r of v.rules || []) {
              if (!result[name]) result[name] = [];
              result[name].push(r as Rule);
            }
          }
        } catch { /* */ }
      }
      setRulesByLib(result);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const totalRules = Object.values(rulesByLib).reduce((sum, rules) => sum + rules.length, 0);
  const filtered = Object.entries(rulesByLib).flatMap(([lib, rules]) =>
    rules
      .filter((r) => !search || r.description.toLowerCase().includes(search.toLowerCase()) || r.id.toLowerCase().includes(search.toLowerCase()) || r.old_name?.toLowerCase().includes(search.toLowerCase()) || r.new_name?.toLowerCase().includes(search.toLowerCase()))
      .map((r) => ({ ...r, library: lib }))
  );

  return (
    <div className="animate-fade-up">
      <div className="mb-8">
        <h1 className="text-[28px] font-bold text-zinc-100 tracking-tight">Migration Rules</h1>
        <p className="text-[14px] text-zinc-400 mt-1">
          {loading ? (
            <span className="inline-block w-48 h-4 skeleton" />
          ) : (
            <>{totalRules} rules across {Object.keys(rulesByLib).length} libraries</>
          )}
        </p>
      </div>

      <div className="mb-8">
        <div className="relative max-w-md">
          <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search rules by name, description, or ID..."
            className="w-full pl-10 pr-4 py-2.5 bg-[#09090b] border border-white/10 rounded-xl text-[13px] text-zinc-100 placeholder-zinc-600 focus:border-blue-500 outline-none transition-all" />
        </div>
      </div>

      {loading ? (
        <div className="space-y-2.5">
          {[1, 2, 3, 4, 5].map((i) => <div key={i} className="h-16 skeleton rounded-xl" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-[#18181b] rounded-xl border border-white/10 p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mx-auto mb-5">
            <svg className="w-8 h-8 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-[15px] font-semibold text-zinc-100 mb-1">No rules found</p>
          <p className="text-[13px] text-zinc-500">{search ? "Try a different search term" : "No libraries with rules yet"}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((rule) => {
            const key = `${rule.library}-${rule.id}`;
            const isOpen = expanded === key;
            return (
              <div key={key} className="bg-[#18181b] rounded-xl border border-white/10 overflow-hidden hover:bg-white/5 transition-all">
                <button onClick={() => setExpanded(isOpen ? null : key)}
                  className="w-full flex items-center gap-4 p-4 text-left">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-white/5 border border-white/10 text-zinc-400">
                        {CT_LABELS[rule.change_type] || rule.change_type}
                      </span>
                      <span className="text-[11px] font-medium text-zinc-500">{rule.library}</span>
                      <span className={`text-[11px] font-medium px-2 py-0.5 rounded-md ${
                        rule.safety === "safe" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                        rule.safety === "review_required" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                        "bg-red-500/10 text-red-400 border border-red-500/20"
                      }`}>{rule.safety.replace("_", " ")}</span>
                    </div>
                    <p className="text-[13px] text-zinc-300 truncate">{rule.description}</p>
                    {(rule.old_name || rule.new_name) && (
                      <p className="font-mono text-[12px] text-zinc-400 mt-0.5">{rule.old_name || "—"} → {rule.new_name || "—"}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <div className="w-12 h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${
                        rule.confidence_hint === "high" ? "bg-emerald-500" :
                        rule.confidence_hint === "medium" ? "bg-amber-500" : "bg-red-500"
                      }`} style={{ width: rule.confidence_hint === "high" ? "90%" : rule.confidence_hint === "medium" ? "60%" : "30%" }} />
                    </div>
                    <svg className={`w-4 h-4 text-zinc-500 transition-transform ${isOpen ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </button>
                {isOpen && (
                  <div className="px-4 pb-4 border-t border-white/10 pt-3 animate-fade-in">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-[12px]">
                      <div><span className="text-zinc-500 font-medium block mb-0.5">ID</span><span className="text-zinc-300 font-mono">{rule.id}</span></div>
                      <div><span className="text-zinc-500 font-medium block mb-0.5">Type</span><span className="text-zinc-300">{rule.change_type}</span></div>
                      <div><span className="text-zinc-500 font-medium block mb-0.5">Library</span><span className="text-zinc-300">{rule.library}</span></div>
                      <div><span className="text-zinc-500 font-medium block mb-0.5">Tags</span><span className="text-zinc-300">{rule.tags?.join(", ") || "—"}</span></div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
