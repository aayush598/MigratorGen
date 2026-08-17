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
  rename_import: "Rename import",
  rename_function: "Rename function",
  rename_class: "Rename class",
  rename_attribute: "Rename attribute",
  add_argument: "Add argument",
  remove_argument: "Remove argument",
  move_to_module: "Move to module",
  deprecate_function: "Deprecate function",
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
      // Try built-in library first
      const libData = await api.libraries.get(id);
      const builtinPack: Pack = {
        id: id,
        name: libData.name || id,
        library: id,
        description: (libData as { description?: string }).description || "",
        published: true,
        created_at: "",
        versions: (libData.versions || []).map((v: { version: string; rules?: unknown[] }) => ({
          version: v.version,
          rules: (v.rules || []) as Rule[],
        })),
      };
      setPack(builtinPack);
      setIsBuiltin(true);
      setEditName(builtinPack.name);
      setEditDesc(builtinPack.description);
    } catch {
      // Try user pack
      try {
        const data = await api.userPacks.get(id);
        const userPack: Pack = {
          id: data.id,
          name: data.name,
          library: data.library,
          description: data.description || "",
          published: (data as { published?: boolean }).published || (data as { is_published?: boolean }).is_published || false,
          created_at: (data as { created_at?: string }).created_at || "",
          versions: (data.versions || []).map((v: { version: string; rules?: unknown[] }) => ({
            version: v.version,
            rules: (v.rules || []) as Rule[],
          })),
        };
        setPack(userPack);
        setIsBuiltin(false);
        setEditName(userPack.name);
        setEditDesc(userPack.description);
      } catch {
        setPack(null);
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { loadPack(); }, [id, loadPack]);

  const handlePublish = async () => {
    if (!pack) return;
    setSaving(true);
    try {
      if (pack.published) {
        await api.userPacks.unpublish(id);
      } else {
        await api.userPacks.publish(id);
      }
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
    try {
      await api.userPacks.delete(id);
      router.push("/libraries");
    } catch { /* */ }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 bg-gray-100 rounded-lg w-1/3 animate-pulse" />
        <div className="h-4 bg-gray-100 rounded w-2/3 animate-pulse" />
        <div className="h-64 bg-gray-100 rounded-xl animate-pulse" />
      </div>
    );
  }

  if (!pack) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-500 font-medium">Library not found</p>
        <Link href="/libraries" className="text-sm text-blue-600 hover:text-blue-700 mt-2 inline-block">Back to libraries</Link>
      </div>
    );
  }

  const currentRules = pack.versions[selectedVersion]?.rules || [];

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-3">
          <Link href="/libraries" className="hover:text-gray-600 transition-colors">Libraries</Link>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          <span className="text-gray-700">{pack.name}</span>
        </div>

        <div className="flex items-start justify-between">
          <div className="flex-1">
            {editing ? (
              <div className="space-y-3 max-w-lg">
                <input type="text" value={editName} onChange={(e) => setEditName(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-lg font-bold text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                <textarea value={editDesc} onChange={(e) => setEditDesc(e.target.value)} rows={2}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none" />
                <div className="flex gap-2">
                  <button onClick={handleSave} disabled={saving}
                    className="bg-blue-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
                    {saving ? "Saving..." : "Save"}
                  </button>
                  <button onClick={() => setEditing(false)}
                    className="border border-gray-300 text-gray-700 px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold text-gray-900">{pack.name}</h1>
                  <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${pack.published ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {pack.published ? "Published" : "Draft"}
                  </span>
                </div>
                {pack.description && <p className="text-gray-500 mt-1">{pack.description}</p>}
                <p className="text-xs text-gray-400 mt-2 font-mono">Slug: {pack.library}</p>
              </>
            )}
          </div>

          <div className="flex items-center gap-2 ml-4">
            {!isBuiltin && !editing && (
              <button onClick={() => setEditing(true)}
                className="border border-gray-300 text-gray-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors flex items-center gap-1.5">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Edit
              </button>
            )}
            {!isBuiltin && (
              <button onClick={handlePublish} disabled={saving}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
                  pack.published
                    ? "border border-gray-300 text-gray-700 hover:bg-gray-50"
                    : "bg-green-600 text-white hover:bg-green-700"
                } disabled:opacity-50`}>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  {pack.published ? (
                    <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  )}
                </svg>
                {pack.published ? "Unpublish" : "Publish"}
              </button>
            )}
            {!isBuiltin && (
              <button onClick={handleDelete}
                className="border border-gray-300 text-red-600 px-3 py-2 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors flex items-center gap-1.5">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Version tabs */}
      <div className="border-b border-gray-200 mb-6">
        <div className="flex gap-0 overflow-x-auto -mb-px">
          {pack.versions.map((v, idx) => (
            <button
              key={idx}
              onClick={() => setSelectedVersion(idx)}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                idx === selectedVersion
                  ? "border-blue-600 text-blue-700"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              v{v.version}
              <span className="ml-1.5 text-xs text-gray-400">({v.rules.length})</span>
            </button>
          ))}
        </div>
      </div>

      {/* Rules table */}
      {currentRules.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <svg className="w-12 h-12 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <p className="text-gray-500 font-medium">No rules in this version</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="text-left px-4 py-3 font-medium text-gray-500 w-8">#</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Type</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Description</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Old</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">New</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Safety</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {currentRules.map((rule, idx) => (
                  <tr key={rule.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-gray-400 text-xs">{idx + 1}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                        {CHANGE_TYPE_LABELS[rule.change_type] || rule.change_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-700 max-w-xs truncate">{rule.description}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">{rule.old_name || rule.old_module || "—"}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">{rule.new_name || rule.new_module || "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        rule.safety === "safe" ? "bg-green-50 text-green-700" :
                        rule.safety === "review_required" ? "bg-yellow-50 text-yellow-700" :
                        "bg-red-50 text-red-700"
                      }`}>{rule.safety.replace("_", " ")}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${
                            rule.confidence_hint === "high" ? "bg-green-500" :
                            rule.confidence_hint === "medium" ? "bg-yellow-500" : "bg-red-500"
                          }`} style={{ width: rule.confidence_hint === "high" ? "90%" : rule.confidence_hint === "medium" ? "60%" : "30%" }} />
                        </div>
                        <span className="text-xs text-gray-500">{rule.confidence_hint}</span>
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
      <div className="mt-6">
        <Link
          href={`/migrations/new?library=${pack.library}`}
          className="inline-flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
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
