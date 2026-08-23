"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import {
  ArrowLeft,
  ArrowRight,
  Download,
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  Pencil,
  Trash2,
  Upload,
  Undo2,
  RefreshCw,
} from "lucide-react";
import { client } from "@/lib/api-client";
import type { SafetyLevel } from "@/schemas";
import { Card, Badge } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { UpdatePackModal } from "@/components/update-pack-modal";
import { toast } from "@/stores/ui-store";

const safetyBadge: Record<string, { tone: "success" | "warning" | "danger"; icon: React.ElementType }> = {
  safe: { tone: "success", icon: ShieldCheck },
  review_required: { tone: "warning", icon: ShieldAlert },
  risky: { tone: "danger", icon: ShieldAlert },
};

export default function LibraryDetailPage({ params }: { params: { id: string } }) {
  const name = decodeURIComponent(params.id);
  const router = useRouter();

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [togglingPublish, setTogglingPublish] = useState(false);
  const [loadingForEdit, setLoadingForEdit] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [updateOpen, setUpdateOpen] = useState(false);

  const { data: library, isLoading, error, mutate } = useSWR(
    `library:${name}`,
    () => client.current.libraries.get(name),
    { revalidateOnFocus: false },
  );

  const isCustom = library?.source === "user";

  const { data: userPacks } = useSWR(
    isCustom ? `user-pack-for:${name}` : null,
    () => client.current.packs.list(),
    { revalidateOnFocus: false },
  );
  const packRecord = userPacks?.find((p) => p.library === name || p.name === name);

  const handleDelete = async () => {
    if (!packRecord) return;
    setDeleting(true);
    try {
      await client.current.packs.delete(packRecord.id);
      toast.success(`Library "${name}" deleted`);
      router.push("/libraries");
      router.refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete library");
      setDeleting(false);
    }
  };

  const handleTogglePublish = async () => {
    if (!packRecord) return;
    setTogglingPublish(true);
    try {
      if (packRecord.is_published) {
        await client.current.packs.unpublish(packRecord.id);
        toast.success("Library unpublished");
      } else {
        await client.current.packs.publish(packRecord.id);
        toast.success("Library published");
      }
      await mutate();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update publish state");
    } finally {
      setTogglingPublish(false);
    }
  };

  const handleEdit = async () => {
    if (!packRecord) return;
    setLoadingForEdit(true);
    try {
      const detail = await client.current.packs.get(packRecord.id);
      const { usePackBuilderStore } = await import("@/stores/pack-builder-store");
      usePackBuilderStore.getState().loadForEdit({
        id: detail.id,
        name: detail.name,
        description: detail.description,
        library: detail.library,
        versions: (detail.versions ?? []).map((v) => ({
          version: v.version,
          release_date: v.release_date ?? "",
          notes: v.notes ?? "",
          rules: (v.rules ?? []) as never[],
        })),
      });
      router.push("/libraries/new");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load library for editing");
      setLoadingForEdit(false);
    }
  };

  const handleExport = async (incremental = false) => {
    setExporting(true);
    try {
      if (isCustom && packRecord) {
        await client.current.packs.exportPack(packRecord.id, incremental);
      } else {
        const url = new URL(`/api/v1/libraries/${encodeURIComponent(name)}/export`, window.location.origin);
        const res = await fetch(url.toString(), { credentials: "include" });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
          throw new Error(err.error || `HTTP ${res.status}`);
        }
        const blob = await res.blob();
        const disposition = res.headers.get("Content-Disposition") ?? "";
        const match = disposition.match(/filename="?(.+?)"?$/);
        const filename = match?.[1] ?? `${name}-migration-pack.zip`;
        const objectUrl = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = objectUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(objectUrl);
      }
      toast.success(incremental ? "Update pack downloaded" : "Full migration pack downloaded");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to export library");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="animate-fade-up">
      <div className="mb-6">
        <Link href="/libraries" className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 transition-colors hover:text-slate-900">
          <ArrowLeft className="h-3 w-3" /> All libraries
        </Link>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl border border-slate-200 bg-white font-mono text-sm font-bold text-slate-700">
              {name.slice(0, 2).toUpperCase()}
            </span>
            <div>
              <h1 className="font-mono text-xl font-bold tracking-tight text-slate-900">{name}</h1>
              <p className="mt-0.5 text-xs text-slate-500">{library?.description || "Migration rules pack"}</p>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                {isCustom ? <Badge tone="info">Custom</Badge> : <Badge>Built-in</Badge>}
                {isCustom && packRecord && (
                  packRecord.is_published
                    ? <Badge tone="success">Published</Badge>
                    : <Badge tone="warning">Draft</Badge>
                )}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {isCustom && packRecord && (
              <>
                <Button variant="secondary" size="sm" onClick={handleEdit} loading={loadingForEdit}>
                  <Pencil className="h-3.5 w-3.5" /> Edit
                </Button>
                <Button variant="secondary" size="sm" onClick={() => handleExport(false)} loading={exporting}>
                  <Download className="h-3.5 w-3.5" /> Export
                </Button>
                <Button variant="secondary" size="sm" onClick={() => setUpdateOpen(true)}>
                  <RefreshCw className="h-3.5 w-3.5" /> Update Only
                </Button>
                <Button variant="secondary" size="sm" onClick={handleTogglePublish} loading={togglingPublish}>
                  {packRecord.is_published ? (
                    <><Undo2 className="h-3.5 w-3.5" /> Unpublish</>
                  ) : (
                    <><Upload className="h-3.5 w-3.5" /> Publish</>
                  )}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setDeleteOpen(true)}
                  className="text-red-600 hover:bg-red-50 hover:text-red-700"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Delete
                </Button>
              </>
            )}
            {!isCustom && (
              <Button variant="secondary" size="sm" onClick={() => handleExport(false)} loading={exporting}>
                <Download className="h-3.5 w-3.5" /> Export Built-in
              </Button>
            )}
            <Link
              href={`/migrations/new?library=${encodeURIComponent(name)}`}
              className="btn-press inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-800"
            >
              Migrate with this pack <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {isLoading && <div className="skeleton h-64 w-full rounded-2xl" />}
      {error && (
        <Card className="p-8 text-center">
          <p className="text-sm text-red-500">{error.message}</p>
          <Button variant="secondary" size="sm" className="mt-4" onClick={() => mutate()}>
            Retry
          </Button>
        </Card>
      )}

      {!isLoading && !error && (
        <div className="space-y-5">
          {(library?.versions ?? []).map((version) => (
            <Card key={version.version} className="overflow-hidden">
              <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/50 px-5 py-3">
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-sm font-bold text-slate-900">v{version.version}</span>
                  {version.release_date && (
                    <span className="text-xs text-slate-400">{version.release_date}</span>
                  )}
                </div>
                <Badge>{version.rules.length} rules</Badge>
              </div>

              {version.notes && (
                <p className="border-b border-slate-50 px-5 py-2.5 text-xs italic text-slate-500">{version.notes}</p>
              )}

              <div className="divide-y divide-slate-50">
                {version.rules.map((rule) => {
                  const safety = safetyBadge[(rule.safety as SafetyLevel) ?? "safe"] ?? safetyBadge.safe;
                  const Icon = safety.icon;
                  return (
                    <div key={rule.id} className="flex items-start gap-3 px-5 py-3.5 hover:bg-slate-50/50">
                      <Icon
                        className={`mt-0.5 h-4 w-4 shrink-0 ${
                          safety.tone === "success" ? "text-emerald-500" : safety.tone === "warning" ? "text-amber-500" : "text-red-400"
                        }`}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] font-medium text-slate-500">
                            {rule.id}
                          </span>
                          <span className="rounded bg-sky-50 px-1.5 py-0.5 font-mono text-[10px] text-sky-600">
                            {rule.change_type}
                          </span>
                          {rule.old_name && rule.new_name && (
                            <span className="font-mono text-xs text-slate-600">
                              {rule.old_name} → {rule.new_name}
                            </span>
                          )}
                          {rule.function_name && (
                            <span className="font-mono text-xs text-slate-500">fn: {rule.function_name}</span>
                          )}
                          {rule.argument_name && (
                            <span className="font-mono text-xs text-slate-500">arg: {rule.argument_name}</span>
                          )}
                        </div>
                        <p className="mt-1 text-xs leading-relaxed text-slate-500">{rule.description || "No description"}</p>
                      </div>
                      <Badge tone={safety.tone}>{rule.safety}</Badge>
                    </div>
                  );
                })}
                {version.rules.length === 0 && (
                  <p className="flex items-center justify-center gap-2 py-8 text-xs text-slate-300">
                    <ShieldQuestion className="h-4 w-4" /> No rules defined for this version
                  </p>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Button variant="secondary" size="sm" className="mt-8" onClick={() => history.back()}>
        <ArrowLeft className="h-3 w-3" /> Back
      </Button>

      <Modal open={deleteOpen} onClose={() => setDeleteOpen(false)} title="Delete custom library">
        <p className="text-sm leading-relaxed text-slate-600">
          Are you sure you want to delete <span className="font-mono font-semibold text-slate-900">{name}</span>?
          Its versions and rules will be permanently removed. Built-in libraries are not affected.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={() => setDeleteOpen(false)}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleDelete}
            loading={deleting}
            className="bg-red-600 hover:bg-red-700"
          >
            <Trash2 className="h-3.5 w-3.5" /> Delete library
          </Button>
        </div>
      </Modal>

      {isCustom && packRecord && (
        <UpdatePackModal
          open={updateOpen}
          onClose={() => setUpdateOpen(false)}
          packId={packRecord.id}
          packName={packRecord.name || name}
          libraryName={name}
        />
      )}
    </div>
  );
}
