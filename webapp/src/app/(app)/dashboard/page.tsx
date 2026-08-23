"use client";

import { useEffect } from "react";
import Link from "next/link";
import useSWR from "swr";
import { ArrowRight, RefreshCw, Layers, Zap, Clock } from "lucide-react";
import { client } from "@/lib/api-client";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/card";
import { useMigrationStore } from "@/stores/migration-store";

export default function DashboardPage() {
  const runs = useMigrationStore((s) => s.runs);
  const lastRunAt = useMigrationStore((s) => s.lastRunAt);
  const clearRuns = useMigrationStore((s) => s.clearRuns);

  const { data: libraries, isLoading } = useSWR("libraries", () => client.current.libraries.list(), {
    revalidateOnFocus: false,
  });

  useEffect(() => {
    if (runs.length === 0 && typeof window !== "undefined") {
      const legacyCount = parseInt(localStorage.getItem("mg_migrations") || "0");
      if (legacyCount > 0 && !localStorage.getItem("mg_last_run")) {
        localStorage.removeItem("mg_migrations");
      }
    }
  }, [runs.length]);

  const libraryEntries = Object.entries(libraries ?? {});
  const totalRules = libraryEntries.reduce((sum, [, lib]) => sum + (lib.rule_count ?? 0), 0);

  const statCards = [
    {
      label: "Migrations Run",
      value: runs.length,
      icon: RefreshCw,
    },
    {
      label: "Libraries",
      value: libraryEntries.length,
      icon: Layers,
    },
    {
      label: "Total Rules",
      value: totalRules,
      icon: Zap,
    },
  ];

  return (
    <div className="animate-fade-up">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[28px] font-bold tracking-tight text-slate-900">Welcome back</h1>
            {lastRunAt && (
              <Badge tone="success">
                <Clock className="h-3 w-3" />
                Last run {formatTime(lastRunAt)}
              </Badge>
            )}
          </div>
          <p className="mt-1 text-sm text-slate-500">Here&apos;s what&apos;s happening with your migrations today.</p>
        </div>
        <Link
          href="/migrations/new"
          className="btn-press inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
        >
          New migration
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <div className="mb-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {statCards.map((card) => (
          <Card key={card.label} className="card-hover p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{card.label}</p>
                <p className="mt-1.5 text-3xl font-bold tabular-nums tracking-tight text-slate-900">
                  {isLoading && card.label !== "Migrations Run" ? (
                    <span className="skeleton inline-block h-9 w-16" />
                  ) : (
                    card.value
                  )}
                </p>
              </div>
              <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-slate-50">
                <card.icon className="h-5 w-5 text-slate-600" />
              </span>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Recent migrations</h2>
            {runs.length > 0 && (
              <Button variant="ghost" size="sm" onClick={clearRuns}>
                Clear history
              </Button>
            )}
          </div>
          {runs.length === 0 ? (
            <EmptyState
              icon={<RefreshCw className="h-5 w-5" />}
              title="No migrations yet"
              description="Run your first migration to see it here."
              action={
                <Link href="/migrations/new" className="btn-press inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800">
                  Start migrating <ArrowRight className="h-3 w-3" />
                </Link>
              }
            />
          ) : (
            <div className="space-y-2">
              {runs.slice(0, 5).map((run) => (
                <Card key={run.id} className="card-hover flex items-center justify-between p-4">
                  <div className="min-w-0">
                    <p className="truncate font-mono text-xs font-medium text-slate-900">{run.library}</p>
                    <p className="mt-0.5 text-xs text-slate-400">{formatTime(run.timestamp)} · {run.changeCount} changes</p>
                  </div>
                  <Badge tone={run.wasModified ? "success" : "default"}>
                    {run.wasModified ? "Modified" : "No changes"}
                  </Badge>
                </Card>
              ))}
              <Link href="/migrations" className="mt-3 block text-center text-xs font-medium text-slate-500 transition-colors hover:text-slate-900">
                View all →
              </Link>
            </div>
          )}
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Library packs</h2>
            <Link href="/libraries" className="text-xs font-medium text-slate-500 transition-colors hover:text-slate-900">
              Browse all →
            </Link>
          </div>
          {libraryEntries.length === 0 ? (
            <EmptyState icon={<Layers className="h-5 w-5" />} title="Loading libraries…" />
          ) : (
            <div className="space-y-2">
              {libraryEntries.slice(0, 5).map(([name, lib]) => (
                <Link key={name} href={`/libraries/${encodeURIComponent(name)}`}>
                  <Card className="card-hover flex items-center justify-between p-4">
                    <div className="min-w-0">
                      <p className="truncate font-mono text-xs font-medium text-slate-900">{name}</p>
                      <p className="mt-0.5 truncate text-xs text-slate-400">{lib.description || "Migration rules pack"}</p>
                    </div>
                    <Badge>{lib.rule_count} rules</Badge>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function formatTime(ts: number): string {
  const diff = Date.now() - ts;
  if (diff < 60_000) return "just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return new Date(ts).toLocaleDateString();
}
