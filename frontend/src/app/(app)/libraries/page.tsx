"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export default function LibrariesPage() {
  const [libs, setLibs] = useState<Record<string, { rule_count: number; source: string; description?: string }>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.libraries.list().then((d) => setLibs(d.libraries)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const filtered = Object.entries(libs).filter(([name]) =>
    name.toLowerCase().includes(search.toLowerCase())
  );

  const totalRules = Object.values(libs).reduce((sum, l) => sum + (l.rule_count || 0), 0);

  return (
    <div className="animate-fade-up">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-[28px] font-bold text-zinc-100 tracking-tight">Libraries</h1>
          <p className="text-[14px] text-zinc-400 mt-1">
            {loading ? (
              <span className="inline-block w-32 h-4 skeleton" />
            ) : (
              <>{totalRules} rules across {Object.keys(libs).length} libraries</>
            )}
          </p>
        </div>
        <Link
          href="/libraries/new"
          className="inline-flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-xl text-[13px] font-semibold hover:bg-blue-700 transition-all btn-press"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Library
        </Link>
      </div>

      {/* Search */}
      <div className="mb-8">
        <div className="relative max-w-md">
          <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search libraries..."
            className="w-full pl-10 pr-4 py-2.5 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 placeholder-zinc-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all"
          />
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-[#18181b] rounded-xl border border-white/10 p-5">
              <div className="flex items-start gap-3 mb-4">
                <div className="w-11 h-11 skeleton rounded-xl" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 skeleton w-1/2" />
                  <div className="h-3 skeleton w-1/4" />
                </div>
              </div>
              <div className="h-3 skeleton w-3/4" />
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-[#18181b] rounded-xl border border-white/10 p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mx-auto mb-5">
            <svg className="w-8 h-8 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
            </svg>
          </div>
          <p className="text-[15px] font-semibold text-zinc-100 mb-1">No libraries found</p>
          <p className="text-[13px] text-zinc-400 mb-5">
            {search ? "Try a different search term" : "Create your first migration library to get started"}
          </p>
          {!search && (
            <Link href="/libraries/new" className="inline-flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-xl text-[13px] font-semibold hover:bg-blue-700 transition-all btn-press">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              Create Library
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(([name, info], i) => (
            <Link
              key={name}
              href={`/libraries/${encodeURIComponent(name)}`}
              className={`animate-fade-up card-hover bg-[#18181b] rounded-xl border border-white/10 p-5 group`}
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-blue-500/10 to-violet-500/10 flex items-center justify-center border border-white/10 group-hover:border-blue-500/40 transition-colors">
                    <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-[14px] font-semibold text-zinc-100 group-hover:text-blue-400 transition-colors capitalize">{name.replace(/-/g, " ")}</h3>
                  </div>
                </div>
                <span className={`text-[11px] font-medium px-2 py-0.5 rounded-md ${
                  info.source === "builtin"
                    ? "bg-blue-400/10 text-blue-300 border border-blue-400/20"
                    : "bg-white/5 text-zinc-400 border border-white/10"
                }`}>
                  {info.source}
                </span>
              </div>

              <div className="flex items-center gap-5 text-[12px] text-zinc-500">
                <span className="flex items-center gap-1.5">
                  <svg className="w-3.5 h-3.5 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {info.rule_count} rules
                </span>
                <span className="flex items-center gap-1.5 text-blue-400 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                  View details
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                  </svg>
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
