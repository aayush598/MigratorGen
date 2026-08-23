"use client";

import Link from "next/link";
import useSWR from "swr";
import { ArrowRight, Layers, Plus } from "lucide-react";
import { client } from "@/lib/api-client";
import { Card, Badge, EmptyState } from "@/components/ui/card";

export default function LibrariesPage() {
  const { data, isLoading, error } = useSWR("libraries", () => client.current.libraries.list());
  const libraries = data ?? {};
  const libraryEntries: [string, { name: string; rule_count: number; source: string; description?: string }][] =
    Object.entries(libraries).map(
      ([name, lib]) => [name, { ...lib }] as [string, { name: string; rule_count: number; source: string; description?: string }],
    );
  const totalRules = libraryEntries.reduce((sum, [, lib]) => sum + (lib.rule_count ?? 0), 0);

  return (
    <div className="animate-fade-up">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-bold tracking-tight text-slate-900">Libraries</h1>
          <p className="mt-1 text-sm text-slate-500">Migration packs available to transform your code.</p>
        </div>
        <Link
          href="/libraries/new"
          className="btn-press inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-800"
        >
          <Plus className="h-3.5 w-3.5" />
          New library
        </Link>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="skeleton h-36 rounded-2xl" />
          ))}
        </div>
      )}

      {error && (
        <EmptyState icon={<Layers className="h-5 w-5" />} title="Failed to load libraries" description={error.message} />
      )}

      {!isLoading && !error && Object.keys(libraries ?? {}).length === 0 && (
        <EmptyState
          icon={<Layers className="h-5 w-5" />}
          title="No library packs yet"
          description="Create a custom migration pack or use the built-in ones to transform your code."
          action={
            <Link
              href="/libraries/new"
              className="btn-press inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-800"
            >
              <Plus className="h-3.5 w-3.5" />
              Create your first library
            </Link>
          }
        />
      )}

      {!isLoading && !error && libraryEntries.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {libraryEntries.map(([name, lib], i) => (
            <Link key={name} href={`/libraries/${encodeURIComponent(name)}`} className={`animate-fade-up stagger-${Math.min(i + 1, 12)}`}>
              <Card className="card-hover group flex h-full flex-col p-5">
                <div className="flex items-start justify-between">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 font-mono text-xs font-bold text-slate-600">
                    {name.slice(0, 2).toUpperCase()}
                  </span>
                  {lib.source === "user" ? (
                    <Badge tone="info">Custom</Badge>
                  ) : (
                    <Badge>Built-in</Badge>
                  )}
                </div>
                <h3 className="mt-3 truncate font-mono text-sm font-semibold text-slate-900">{name}</h3>
                <p className="mt-1 line-clamp-2 flex-1 text-xs leading-relaxed text-slate-500">
                  {lib.description || "Migration rules pack"}
                </p>
                <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
                  <span className="text-xs text-slate-400">{lib.rule_count} rules</span>
                  <ArrowRight className="h-3.5 w-3.5 text-slate-300 transition-all group-hover:translate-x-0.5 group-hover:text-slate-600" />
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
