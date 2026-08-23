"use client";

import Link from "next/link";
import { ArrowRight, RefreshCw } from "lucide-react";
import { Card, Badge, EmptyState } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useMigrationStore } from "@/stores/migration-store";

export default function MigrationsPage() {
  const runs = useMigrationStore((s) => s.runs);
  const clearRuns = useMigrationStore((s) => s.clearRuns);

  return (
    <div className="animate-fade-up">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-bold tracking-tight text-slate-900">Migrations</h1>
          <p className="mt-1 text-sm text-slate-500">History of code transformations run from this workspace.</p>
        </div>
        <div className="flex items-center gap-2">
          {runs.length > 0 && (
            <Button variant="secondary" size="sm" onClick={clearRuns}>
              Clear all
            </Button>
          )}
          <Link
            href="/migrations/new"
            className="btn-press inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-800"
          >
            New migration <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>

      {runs.length === 0 ? (
        <EmptyState
          icon={<RefreshCw className="h-5 w-5" />}
          title="No migration runs yet"
          description="Every migration you apply will be recorded here with its diff summary."
          action={
            <Link href="/migrations/new" className="btn-press inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800">
              Run your first migration <ArrowRight className="h-3 w-3" />
            </Link>
          }
        />
      ) : (
        <Card className="overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-400">
                <th className="px-5 py-3 font-medium">Library</th>
                <th className="px-5 py-3 font-medium">Versions</th>
                <th className="px-5 py-3 font-medium">Changes</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 text-right font-medium">When</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/60">
                  <td className="px-5 py-3.5 font-mono text-xs font-medium text-slate-900">{run.library}</td>
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-500">
                    {run.sourceVersion || "default"} → {run.targetVersion || "latest"}
                  </td>
                  <td className="px-5 py-3.5 tabular-nums text-slate-600">{run.changeCount}</td>
                  <td className="px-5 py-3.5">
                    <Badge tone={run.wasModified ? "success" : "default"}>
                      {run.wasModified ? "Modified" : "Unchanged"}
                    </Badge>
                  </td>
                  <td className="px-5 py-3.5 text-right text-xs text-slate-400">{formatTime(run.timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
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
