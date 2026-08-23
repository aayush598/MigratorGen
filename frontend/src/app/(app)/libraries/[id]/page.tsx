"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

interface Rule {
  id: string;
  change_type: string;
  description: string;
  old_name?: string;
  new_name?: string;
  old_module?: string;
  new_module?: string;
  function_name?: string;
  argument_name?: string;
  safety: string;
  confidence_hint: string;
  tags: string[];
  version_introduced?: string;
}

interface Version {
  version: string;
  release_date?: string;
  rules: Rule[];
}

interface Pack {
  id: string;
  name: string;
  library: string;
  description: string;
  published: boolean;
  created_at: string;
  versions: Version[];
}

const CHANGE_TYPE_LABELS: Record<string, string> = {
  rename_import: "Rename import", rename_function: "Rename function", rename_class: "Rename class",
  rename_attribute: "Rename attribute", add_argument: "Add argument", remove_argument: "Remove argument",
  move_to_module: "Move to module", deprecate_function: "Deprecate function",
};

export default function LibraryDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;

  const [pack, setPack] = useState<Pack | null>(null);
  const [isBuiltin, setIsBuiltin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedVersion, setSelectedVersion] = useState(0);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [saving, setSaving] = useState(false);

  const loadPack = useCallback(async () => {
    try {
      const libData = await api.libraries.get(id);
      const builtinPack: Pack = {
        id, name: libData.name || id, library: id,
        description: (libData as { description?: string }).description || "",
        published: true, created_at: "",
        versions: (libData.versions || []).map((v: { version: string; rules?: unknown[] }) => ({
          version: v.version, rules: (v.rules || []) as Rule[],
        })),
      };
      setPack(builtinPack);
      setIsBuiltin(true);
      setEditName(builtinPack.name);
      setEditDesc(builtinPack.description);
    } catch {
      try {
        const data = await api.userPacks.get(id);
        const userPack: Pack = {
          id: data.id, name: data.name, library: data.library,
          description: data.description || "",
          published: (data as { published?: boolean }).published || (data as { is_published?: boolean }).is_published || false,
          created_at: (data as { created_at?: string }).created_at || "",
          versions: (data.versions || []).map((v: { version: string; rules?: unknown[] }) => ({
            version: v.version, rules: (v.rules || []) as Rule[],
          })),
        };
        setPack(userPack);
        setIsBuiltin(false);
        setEditName(userPack.name);
        setEditDesc(userPack.description);
      } catch { setPack(null); }
    } finally { setLoading(false); }
  }, [id]);

  useEffect(() => { loadPack(); }, [id, loadPack]);

  const handlePublish = async () => {
    if (!pack) return;
    setSaving(true);
    try {
      if (pack.published) await api.userPacks.unpublish(id);
      else await api.userPacks.publish(id);
      await loadPack();
    } catch { /* */ }
    setSaving(false);
  };

  const handleSave = async () => {
    if (!pack) return;
    setSaving(true);
    try {
      await api.userPacks.update(id, { name: editName, description: editDesc });
      setEditing(false);
      await loadPack();
    } catch { /* */ }
    setSaving(false);
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this library? This cannot be undone.")) return;
    try { await api.userPacks.delete(id); router.push("/libraries"); } catch { /* */ }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="space-y-3">
          <div className="h-8 skeleton w-1/3" />
          <div className="h-4 skeleton w-2/3" />
        </div>
        <div className="h-12 skeleton w-full" />
        <div className="h-64 skeleton rounded-2xl" />
      </div>
    );
  }

  if (!pack) {
    return (
      <div className="text-center py-24 animate-fade-up">
        <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mx-auto mb-5">
          <svg className="w-8 h-8 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
          </svg>
        </div>
        <p className="text-[15px] font-semibold text-zinc-100 mb-1">Library not found</p>
        <Link href="/libraries" className="text-[13px] text-blue-600 hover:text-blue-700 font-medium">Back to libraries</Link>
      </div>
    );
  }

  const currentRules = pack.versions[selectedVersion]?.rules || [];
  const totalRules = pack.versions.reduce((sum, v) => sum + v.rules.length, 0);

  return (
    <div className="animate-fade-up">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-[13px] text-zinc-500 mb-4">
          <Link href="/libraries" className="hover:text-zinc-300 transition-colors font-medium">Libraries</Link>
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
          <span className="text-zinc-200 font-medium">{pack.name}</span>
        </div>

        <div className="flex items-start justify-between">
          <div className="flex-1">
            {editing ? (
              <div className="space-y-3 max-w-lg">
                <input type="text" value={editName} onChange={(e) => setEditName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[#09090b] border border-white/10 rounded-xl text-[18px] font-bold text-zinc-100 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 outline-none transition-all" />
                <textarea value={editDesc} onChange={(e) => setEditDesc(e.target.value)} rows={2}
                  className="w-full px-3.5 py-2.5 bg-[#09090b] border border-white/10 rounded-xl text-[13px] text-zinc-100 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 outline-none transition-all resize-none" />
                <div className="flex gap-2">
                  <button onClick={handleSave} disabled={saving}
                    className="bg-blue-600 text-white px-4 py-2 rounded-xl text-[13px] font-semibold hover:bg-blue-700 disabled:opacity-50 transition-all btn-press">
                    {saving ? "Saving..." : "Save"}
                  </button>
                  <button onClick={() => setEditing(false)}
                    className="border border-white/10 text-zinc-200 px-4 py-2 rounded-xl text-[13px] font-semibold hover:bg-white/5 transition-colors">
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-3">
                  <h1 className="text-[28px] font-bold text-zinc-100 tracking-tight">{pack.name}</h1>
                  <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-md ${
                    pack.published ? "bg-emerald-400/10 text-emerald-400 border border-emerald-400/20" : "bg-white/5 text-zinc-500"
                  }`}>
                    {pack.published ? "Published" : "Draft"}
                  </span>
                </div>
                {pack.description && <p className="text-[14px] text-zinc-500 mt-1.5">{pack.description}</p>}
                <div className="flex items-center gap-4 mt-3 text-[12px] text-zinc-500">
                  <span className="font-mono">Slug: {pack.library}</span>
                  <span>{totalRules} rules across {pack.versions.length} version{pack.versions.length !== 1 ? "s" : ""}</span>
                </div>
              </>
            )}
          </div>

          <div className="flex items-center gap-2 ml-4">
            {!isBuiltin && !editing && (
              <button onClick={() => setEditing(true)}
                className="border border-white/10 text-zinc-200 px-4 py-2 rounded-xl text-[13px] font-semibold hover:bg-white/5 transition-colors flex items-center gap-1.5 btn-press">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125" />
                </svg>
                Edit
              </button>
            )}
            {!isBuiltin && (
              <button onClick={handlePublish} disabled={saving}
                className={`px-4 py-2 rounded-xl text-[13px] font-semibold transition-all flex items-center gap-1.5 btn-press ${
                  pack.published
                    ? "border border-white/10 text-zinc-200 hover:bg-white/5"
                    : "bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm shadow-emerald-500/20"
                } disabled:opacity-50`}>
                {pack.published ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                )}
                {pack.published ? "Unpublish" : "Publish"}
              </button>
            )}
            {!isBuiltin && (
              <button onClick={handleDelete}
                className="border border-red-500/20 text-red-400 px-4 py-2 rounded-xl text-[13px] font-semibold hover:bg-red-500/10 transition-colors flex items-center gap-1.5 btn-press">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                </svg>
                Delete
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Version tabs */}
      <div className="border-b border-white/10 mb-6">
        <div className="flex gap-0 overflow-x-auto -mb-px">
          {pack.versions.map((v, idx) => (
            <button key={idx} onClick={() => setSelectedVersion(idx)}
              className={`px-5 py-3 text-[13px] font-semibold whitespace-nowrap border-b-2 transition-all ${
                idx === selectedVersion
                  ? "border-blue-500 text-zinc-100"
                  : "border-transparent text-zinc-500 hover:text-zinc-300 hover:border-white/20"
              }`}>
              v{v.version}
              <span className="ml-1.5 text-[11px] font-medium text-zinc-500">({v.rules.length})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Rules table */}
      {currentRules.length === 0 ? (
        <div className="bg-[#18181b] rounded-2xl border border-white/10 p-16 text-center">
          <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mx-auto mb-5">
            <svg className="w-8 h-8 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-[15px] font-semibold text-zinc-100 mb-1">No rules in this version</p>
          <p className="text-[13px] text-zinc-500">Add rules when creating a new version</p>
        </div>
      ) : (
        <div className="bg-[#18181b] rounded-2xl border border-white/10 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-white/5 bg-white/5">
                  <th className="text-left px-5 py-3.5 font-semibold text-zinc-500 w-10">#</th>
                  <th className="text-left px-5 py-3.5 font-semibold text-zinc-500">Type</th>
                  <th className="text-left px-5 py-3.5 font-semibold text-zinc-500">Description</th>
                  <th className="text-left px-5 py-3.5 font-semibold text-zinc-500">Old</th>
                  <th className="text-left px-5 py-3.5 font-semibold text-zinc-500">New</th>
                  <th className="text-left px-5 py-3.5 font-semibold text-zinc-500">Safety</th>
                  <th className="text-left px-5 py-3.5 font-semibold text-zinc-500">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {currentRules.map((rule, idx) => (
                  <tr key={rule.id} className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors">
                    <td className="px-5 py-3.5 text-zinc-500 text-[12px] font-medium">{idx + 1}</td>
                    <td className="px-5 py-3.5">
                      <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-white/5 text-zinc-400">
                        {CHANGE_TYPE_LABELS[rule.change_type] || rule.change_type}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-zinc-200 max-w-xs truncate">{rule.description}</td>
                    <td className="px-5 py-3.5 font-mono text-[12px] text-zinc-400">{rule.old_name || rule.old_module || "—"}</td>
                    <td className="px-5 py-3.5 font-mono text-[12px] text-zinc-400">{rule.new_name || rule.new_module || "—"}</td>
                    <td className="px-5 py-3.5">
                      <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-md ${
                        rule.safety === "safe" ? "bg-emerald-400/10 text-emerald-400 border border-emerald-400/20" :
                        rule.safety === "review_required" ? "bg-amber-400/10 text-amber-400 border border-amber-400/20" :
                        "bg-red-400/10 text-red-400 border border-red-400/20"
                      }`}>{rule.safety.replace("_", " ")}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-white/5 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${
                            rule.confidence_hint === "high" ? "bg-emerald-500" :
                            rule.confidence_hint === "medium" ? "bg-amber-500" : "bg-red-500"
                          }`} style={{ width: rule.confidence_hint === "high" ? "90%" : rule.confidence_hint === "medium" ? "60%" : "30%" }} />
                        </div>
                        <span className="text-[11px] text-zinc-500 font-medium">{rule.confidence_hint}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Use this library */}
      <div className="mt-8">
        <Link
          href={`/migrations/new?library=${pack.library}`}
          className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-xl text-[13px] font-semibold hover:bg-blue-700 transition-all shadow-sm shadow-slate-900/10 btn-press"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
          Use this library
        </Link>
      </div>
    </div>
  );
}
