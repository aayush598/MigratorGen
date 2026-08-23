"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface MigrationRecord {
  id: string;
  library: string;
  timestamp: number;
  result: { transformed_code: string; changes: string[]; was_modified: boolean };
}

export default function MigrationsPage() {
  const [migrations, setMigrations] = useState<MigrationRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("mg_migration_history");
      if (stored) setMigrations(JSON.parse(stored));
    } catch { /* */ }
    setLoading(false);
  }, []);

  const deleteMigration = (timestamp: number) => {
    const updated = migrations.filter((m) => m.timestamp !== timestamp);
    setMigrations(updated);
    localStorage.setItem("mg_migration_history", JSON.stringify(updated));
  };

  const copyResult = (code: string) => { navigator.clipboard.writeText(code); };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    const diff = Date.now() - d.getTime();
    if (diff < 60000) return "Just now";
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <div className="animate-fade-up">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-[28px] font-bold text-zinc-100 tracking-tight">Migrations</h1>
          <p className="text-[14px] text-zinc-400 mt-1">{migrations.length} migration{migrations.length !== 1 ? "s" : ""} in history</p>
        </div>
        <Link href="/migrations/new"
          className="inline-flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-xl text-[13px] font-semibold hover:bg-blue-700 transition-all btn-press">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Migration
        </Link>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => <div key={i} className="h-20 skeleton rounded-xl" />)}
        </div>
      ) : migrations.length === 0 ? (
        <div className="bg-[#18181b] rounded-xl border border-white/10 p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-[#09090b] flex items-center justify-center mx-auto mb-5">
            <svg className="w-8 h-8 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
            </svg>
          </div>
          <p className="text-[15px] font-semibold text-zinc-100 mb-1">No migrations yet</p>
          <p className="text-[13px] text-zinc-400 mb-5">Run your first migration to see it here</p>
          <Link href="/migrations/new" className="inline-flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-xl text-[13px] font-semibold hover:bg-blue-700 transition-all btn-press">
            Start a migration
          </Link>
        </div>
      ) : (
        <div className="space-y-2.5">
          {migrations.map((m) => (
            <div key={m.timestamp} className="bg-[#18181b] rounded-xl border border-white/10 p-4 hover:bg-white/5 transition-all group">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/10 to-violet-500/10 flex items-center justify-center flex-shrink-0 border border-blue-500/20">
                  <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-[13px] font-semibold text-zinc-100 capitalize">{(m.library || "unknown").replace(/-/g, " ")}</p>
                    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-md ${
                      m.result?.was_modified
                        ? "text-emerald-400 bg-emerald-400/10 border border-emerald-400/20"
                        : "bg-white/5 text-zinc-400"
                    }`}>
                      {m.result?.was_modified ? "Modified" : "No changes"}
                    </span>
                  </div>
                  <p className="text-[12px] text-zinc-500 mt-0.5">
                    {m.result?.changes?.length || 0} changes · {formatTime(m.timestamp)}
                  </p>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => copyResult(m.result?.transformed_code || "")}
                    className="p-2 text-zinc-500 hover:text-blue-400 hover:bg-white/5 rounded-lg transition-colors" title="Copy result">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                    </svg>
                  </button>
                  <button onClick={() => deleteMigration(m.timestamp)}
                    className="p-2 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors" title="Delete">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
