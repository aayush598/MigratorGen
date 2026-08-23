"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
}

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [newKeyName, setNewKeyName] = useState("");
  const [creating, setCreating] = useState(false);
  const [newKey, setNewKey] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const loadKeys = () => {
    api.keys.list().then((d) => setKeys(d)).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { loadKeys(); }, []);

  const handleCreate = async () => {
    if (!newKeyName.trim()) return;
    setCreating(true);
    setError("");
    try {
      const result = await api.keys.create(newKeyName, ["migrate", "read"]);
      setNewKey(result.key);
      setNewKeyName("");
      loadKeys();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create key");
    }
    setCreating(false);
  };

  const handleDelete = async (keyId: string) => {
    if (!confirm("Revoke this API key? This cannot be undone.")) return;
    try { await api.keys.delete(keyId); loadKeys(); } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to revoke key");
    }
  };

  const copyKey = () => {
    navigator.clipboard.writeText(newKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="max-w-3xl animate-fade-up">
      <div className="mb-8">
        <h1 className="text-[28px] font-bold text-zinc-100 tracking-tight">API Keys</h1>
        <p className="text-[14px] text-zinc-400 mt-1">Manage API keys for programmatic access</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3.5 mb-6 text-[13px] text-red-400 flex items-center gap-2">
          <svg className="w-4 h-4 text-red-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </div>
      )}

      {/* Create new key */}
      <div className="bg-[#18181b] rounded-xl border border-white/10 p-6 mb-6">
        <h2 className="text-[15px] font-semibold text-zinc-100 mb-4">Create API Key</h2>
        <div className="flex gap-3">
          <input type="text" value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key name (e.g. CI pipeline)"
            className="flex-1 px-3.5 py-2.5 bg-[#09090b] border border-white/10 rounded-xl text-[13px] text-zinc-100 placeholder-zinc-600 focus:border-blue-500 outline-none transition-all"
            onKeyDown={(e) => e.key === "Enter" && handleCreate()} />
          <button onClick={handleCreate} disabled={creating || !newKeyName.trim()}
            className="bg-blue-600 text-white px-5 py-2.5 rounded-xl text-[13px] font-semibold hover:bg-blue-700 disabled:opacity-50 transition-all whitespace-nowrap btn-press">
            {creating ? "Creating..." : "Create Key"}
          </button>
        </div>
      </div>

      {/* Newly created key */}
      {newKey && (
        <div className="bg-emerald-400/10 border border-emerald-400/20 rounded-xl p-5 mb-6 animate-fade-up">
          <div className="flex items-center gap-2 mb-3">
            <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-[13px] font-semibold text-emerald-400">API key created successfully</span>
          </div>
          <p className="text-[12px] text-zinc-400 mb-3">Copy this key now — it won&apos;t be shown again.</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-[#09090b] border border-white/10 rounded-xl px-3.5 py-2.5 text-[13px] font-mono text-zinc-100 break-all">{newKey}</code>
            <button onClick={copyKey}
              className="px-4 py-2.5 border border-white/10 rounded-xl text-[13px] font-semibold text-zinc-300 hover:bg-white/5 transition-colors whitespace-nowrap btn-press">
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        </div>
      )}

      {/* Existing keys */}
      <div className="bg-[#18181b] rounded-xl border border-white/10 overflow-hidden">
        <div className="px-6 py-4 border-b border-white/10">
          <h2 className="text-[15px] font-semibold text-zinc-100">Existing Keys</h2>
        </div>
        {loading ? (
          <div className="p-6 space-y-3">
            {[1, 2].map((i) => <div key={i} className="h-14 skeleton rounded-xl" />)}
          </div>
        ) : keys.length === 0 ? (
          <div className="p-16 text-center">
            <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-4">
              <svg className="w-7 h-7 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
              </svg>
            </div>
            <p className="text-[15px] font-semibold text-zinc-100 mb-1">No API keys yet</p>
            <p className="text-[13px] text-zinc-500">Create one above to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-white/10">
            {keys.map((key) => (
              <div key={key.id} className="flex items-center gap-4 px-6 py-4 hover:bg-white/5 transition-colors">
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-semibold text-zinc-100">{key.name}</p>
                  <div className="flex items-center gap-3 mt-0.5">
                    <code className="text-[12px] text-zinc-500 font-mono">{key.key_prefix}...</code>
                    <div className="flex gap-1">
                      {key.scopes.map((s) => (
                        <span key={s} className="text-[11px] bg-white/5 border border-white/10 text-zinc-400 px-1.5 py-0.5 rounded font-medium">{s}</span>
                      ))}
                    </div>
                  </div>
                </div>
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-md ${key.is_active ? "bg-emerald-400/10 text-emerald-400 border border-emerald-400/20" : "bg-white/5 border border-white/10 text-zinc-500"}`}>
                  {key.is_active ? "Active" : "Revoked"}
                </span>
                {key.is_active && (
                  <button onClick={() => handleDelete(key.id)}
                    className="p-2 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors" title="Revoke">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
