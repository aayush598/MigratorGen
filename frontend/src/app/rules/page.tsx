"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Migration Rules</h1>
        <p className="text-sm text-gray-500 mt-1">
          {loading ? "Loading..." : `${totalRules} rules across ${Object.keys(rulesByLib).length} libraries`}
        </p>
      </div>

      <div className="mb-6">
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search rules by name, description, or ID..."
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => <div key={i} className="h-16 bg-gray-100 rounded-xl animate-pulse" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-500 font-medium">No rules found</p>
          <p className="text-sm text-gray-400 mt-1">{search ? "Try a different search" : "No libraries with rules yet"}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((rule) => {
            const key = `${rule.library}-${rule.id}`;
            const isOpen = expanded === key;
            return (
              <div key={key} className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:border-gray-300 transition-colors">
                <button onClick={() => setExpanded(isOpen ? null : key)}
                  className="w-full flex items-center gap-4 p-4 text-left">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                        {CT_LABELS[rule.change_type] || rule.change_type}
                      </span>
                      <span className="text-xs text-gray-400">{rule.library}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        rule.safety === "safe" ? "bg-green-50 text-green-700" :
                        rule.safety === "review_required" ? "bg-yellow-50 text-yellow-700" :
                        "bg-red-50 text-red-700"
                      }`}>{rule.safety.replace("_", " ")}</span>
                    </div>
                    <p className="text-sm text-gray-700 truncate">{rule.description}</p>
                    {(rule.old_name || rule.new_name) && (
                      <p className="text-xs text-gray-400 font-mono mt-0.5">{rule.old_name || "—"} → {rule.new_name || "—"}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <div className="w-12 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${
                        rule.confidence_hint === "high" ? "bg-green-500" :
                        rule.confidence_hint === "medium" ? "bg-yellow-500" : "bg-red-500"
                      }`} style={{ width: rule.confidence_hint === "high" ? "90%" : rule.confidence_hint === "medium" ? "60%" : "30%" }} />
                    </div>
                    <svg className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </button>
                {isOpen && (
                  <div className="px-4 pb-4 border-t border-gray-100 pt-3">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      <div><span className="text-gray-400 block">ID</span><span className="text-gray-700 font-mono">{rule.id}</span></div>
                      <div><span className="text-gray-400 block">Type</span><span className="text-gray-700">{rule.change_type}</span></div>
                      <div><span className="text-gray-400 block">Library</span><span className="text-gray-700">{rule.library}</span></div>
                      <div><span className="text-gray-400 block">Tags</span><span className="text-gray-700">{rule.tags?.join(", ") || "—"}</span></div>
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
