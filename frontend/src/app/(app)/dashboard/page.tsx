"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState({ migrations: 0, libraries: 0, lastRun: "" });
  const [libs, setLibs] = useState<Record<string, { rule_count: number; source: string }>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const migrations = parseInt(localStorage.getItem("mg_migrations") || "0");
    const lastRun = localStorage.getItem("mg_last_run") || "";
    setStats({ migrations, libraries: 0, lastRun });

    api.libraries.list().then((data) => {
      const count = Object.keys(data.libraries).length;
      setLibs(data.libraries);
      setStats((s) => ({ ...s, libraries: count }));
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const statCards = [
    { label: "Migrations Run", value: stats.migrations, icon: "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15", gradient: "from-blue-500 to-blue-600" },
    { label: "Libraries", value: stats.libraries, icon: "M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z", gradient: "from-emerald-500 to-emerald-600" },
    { label: "Total Rules", value: Object.values(libs).reduce((sum, l) => sum + (l.rule_count || 0), 0), icon: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z", gradient: "from-violet-500 to-violet-600" },
  ];

  const formatTime = (ts: string) => {
    if (!ts) return "Never";
    const d = new Date(ts);
    const diff = Date.now() - d.getTime();
    if (diff < 60000) return "Just now";
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <div className="animate-fade-up">
      {/* Hero */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-[28px] font-bold text-zinc-100 tracking-tight">Welcome back</h1>
          {stats.lastRun && (
            <span className="text-[11px] font-medium px-2 py-0.5 rounded-md bg-emerald-400/10 text-emerald-400 border border-emerald-400/20">
              Last run {formatTime(stats.lastRun)}
            </span>
          )}
        </div>
        <p className="text-[13px] text-zinc-400">Here&apos;s what&apos;s happening with your migrations today.</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
        {statCards.map((card, i) => (
          <div key={card.label} className={`animate-fade-up stagger-${i + 1} card-hover bg-[#18181b] rounded-xl border border-white/10 p-5 relative overflow-hidden group`}>
            <div className="relative flex items-center justify-between">
              <div>
                <p className="text-[13px] font-medium text-zinc-400">{card.label}</p>
                <p className="text-[28px] font-bold text-zinc-100 mt-1 tracking-tight">{loading ? (
                  <span className="inline-block w-12 h-7 skeleton" />
                ) : card.value}</p>
              </div>
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${card.gradient} flex items-center justify-center`}>
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={card.icon} />
                </svg>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Quick Start */}
        <div className="lg:col-span-2 bg-[#18181b] rounded-xl border border-white/10 p-6 animate-fade-up stagger-2">
          <h2 className="text-[13px] font-semibold text-zinc-100 mb-4 uppercase tracking-wider text-zinc-400">Quick start</h2>
          <div className="space-y-2.5">
            <Link href="/migrations/new" className="group flex items-center gap-4 p-3.5 rounded-xl border border-white/10 hover:border-blue-500/30 hover:bg-white/5 transition-all duration-200">
              <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center group-hover:bg-blue-500 transition-colors">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="text-[13px] font-semibold text-zinc-100 group-hover:text-blue-400 transition-colors">New Migration</p>
                <p className="text-[12px] text-zinc-500">Paste code and run transformations</p>
              </div>
              <svg className="w-4 h-4 text-zinc-600 group-hover:text-blue-400 group-hover:translate-x-0.5 transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </Link>
            <Link href="/libraries/new" className="group flex items-center gap-4 p-3.5 rounded-xl border border-white/10 hover:border-emerald-500/30 hover:bg-white/5 transition-all duration-200">
              <div className="w-10 h-10 rounded-xl bg-emerald-600 flex items-center justify-center group-hover:bg-emerald-500 transition-colors">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="text-[13px] font-semibold text-zinc-100 group-hover:text-emerald-400 transition-colors">Create Library</p>
                <p className="text-[12px] text-zinc-500">Define custom migration rules</p>
              </div>
              <svg className="w-4 h-4 text-zinc-600 group-hover:text-emerald-400 group-hover:translate-x-0.5 transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </Link>
            <Link href="/rules" className="group flex items-center gap-4 p-3.5 rounded-xl border border-white/10 hover:border-violet-500/30 hover:bg-white/5 transition-all duration-200">
              <div className="w-10 h-10 rounded-xl bg-violet-600 flex items-center justify-center group-hover:bg-violet-500 transition-colors">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="text-[13px] font-semibold text-zinc-100 group-hover:text-violet-400 transition-colors">Browse Rules</p>
                <p className="text-[12px] text-zinc-500">View all available migration rules</p>
              </div>
              <svg className="w-4 h-4 text-zinc-600 group-hover:text-violet-400 group-hover:translate-x-0.5 transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </Link>
          </div>
        </div>

        {/* Recent Libraries */}
        <div className="lg:col-span-3 bg-[#18181b] rounded-xl border border-white/10 p-6 animate-fade-up stagger-3">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-[13px] font-semibold text-zinc-400 uppercase tracking-wider">Libraries</h2>
            <Link href="/libraries" className="text-[13px] text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1">
              View all
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </Link>
          </div>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-3 p-3">
                  <div className="w-10 h-10 skeleton rounded-xl" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 skeleton w-1/3" />
                    <div className="h-3 skeleton w-1/4" />
                  </div>
                </div>
              ))}
            </div>
          ) : Object.keys(libs).length === 0 ? (
            <div className="text-center py-10">
              <div className="w-14 h-14 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-4">
                <svg className="w-7 h-7 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
                </svg>
              </div>
              <p className="text-[13px] font-medium text-zinc-400 mb-1">No libraries yet</p>
              <Link href="/libraries/new" className="text-[13px] text-blue-400 hover:text-blue-300 font-medium">Create your first library</Link>
            </div>
          ) : (
            <div className="space-y-1.5">
              {Object.entries(libs).slice(0, 5).map(([name, info]) => (
                <Link
                  key={name}
                  href={`/libraries/${encodeURIComponent(name)}`}
                  className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/5 transition-colors group"
                >
                  <div className="w-10 h-10 rounded-xl bg-blue-600/10 border border-white/10 flex items-center justify-center">
                    <svg className="w-4.5 h-4.5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-semibold text-zinc-100 capitalize">{name.replace(/-/g, " ")}</p>
                    <p className="text-[12px] text-zinc-500">{info.rule_count} rules</p>
                  </div>
                  <span className={`text-[11px] font-medium px-2 py-0.5 rounded-md ${
                    info.source === "builtin"
                      ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                      : "bg-white/5 border border-white/10 text-zinc-400"
                  }`}>
                    {info.source}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
