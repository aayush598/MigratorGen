"use client";

import { ArrowLeft, ArrowRight, Plus, Trash2 } from "lucide-react";
import { usePackBuilderStore } from "@/stores/pack-builder-store";
import { Button } from "@/components/ui/button";
import { Input, Textarea, Label } from "@/components/ui/input";
import { Card, Badge } from "@/components/ui/card";

export function VersionsStep({ onBack, onNext }: { onBack: () => void; onNext: () => void }) {
  const versions = usePackBuilderStore((s) => s.versions);
  const selectedIndex = usePackBuilderStore((s) => s.selectedVersionIndex);
  const addVersion = usePackBuilderStore((s) => s.addVersion);
  const removeVersion = usePackBuilderStore((s) => s.removeVersion);
  const updateVersion = usePackBuilderStore((s) => s.updateVersion);
  const selectVersion = usePackBuilderStore((s) => s.selectVersion);

  const current = versions[selectedIndex];

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[280px_1fr]">
      <Card className="p-4">
        <div className="mb-3 flex items-center justify-between px-1">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Versions</h3>
          <Button variant="ghost" size="sm" type="button" onClick={addVersion}>
            <Plus className="h-3.5 w-3.5" /> Add
          </Button>
        </div>
        <div className="space-y-1">
          {versions.map((v, i) => (
            <div
              key={i}
              role="button"
              tabIndex={0}
              onClick={() => selectVersion(i)}
              onKeyDown={(e) => e.key === "Enter" && selectVersion(i)}
              className={`btn-press flex w-full cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors ${
                i === selectedIndex ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              <span className="font-mono text-xs">v{v.version || "?"}</span>
              <span className="flex items-center gap-2">
                <Badge tone={i === selectedIndex ? "info" : "default"}>{v.rules.length}</Badge>
                {versions.length > 1 && (
                  <button
                    type="button"
                    aria-label={`Remove version ${v.version}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      removeVersion(i);
                    }}
                    className="opacity-40 hover:text-red-500 hover:opacity-100"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
              </span>
            </div>
          ))}
        </div>
        <Button variant="secondary" size="sm" type="button" className="mt-4 w-full" onClick={onBack}>
          <ArrowLeft className="h-3 w-3" /> Back to details
        </Button>
      </Card>

      {current && (
        <Card className="p-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="version">Version number</Label>
              <Input
                id="version"
                value={current.version}
                onChange={(e) => updateVersion(selectedIndex, { version: e.target.value })}
                placeholder="1.0.0"
                className="font-mono"
              />
            </div>
            <div>
              <Label htmlFor="release-date">Release date</Label>
              <Input
                id="release-date"
                type="date"
                value={current.release_date}
                onChange={(e) => updateVersion(selectedIndex, { release_date: e.target.value })}
              />
            </div>
          </div>
          <div className="mt-4">
            <Label htmlFor="notes">Release notes</Label>
            <Textarea
              id="notes"
              rows={4}
              value={current.notes}
              onChange={(e) => updateVersion(selectedIndex, { notes: e.target.value })}
              placeholder="Summary of breaking changes in this version…"
            />
          </div>
          <Button type="button" className="mt-5" onClick={onNext}>
            Next: Rules <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </Card>
      )}
    </div>
  );
}
