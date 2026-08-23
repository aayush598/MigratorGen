"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function NewMigrationContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const presetLibrary = searchParams.get("library") || "";

  const [sourceCode, setSourceCode] = useState("");
  const [libraries, setLibraries] = useState<Record<string, { rule_count: number; source: string; versions?: { version: string; rules: unknown[] }[] }>>({});
  const [selectedLib, setSelectedLib] = useState(presetLibrary);
  const [sourceVersion, setSourceVersion] = useState("");
  const [targetVersion, setTargetVersion] = useState("");
  const [preview, setPreview] = useState<{ changes: string[]; change_count: number; average_confidence: number; transformed_code?: string } | null>(null);
  const [result, setResult] = useState<{ transformed_code: string; changes: string[]; was_modified: boolean } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"preview" | "result">("preview");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.libraries.list().then((d) => setLibraries(d.libraries)).catch(() => {});
  }, []);

  useEffect(() => {
    if (presetLibrary && libraries[presetLibrary]) {
      setSelectedLib(presetLibrary);
    }
  }, [presetLibrary, libraries]);

  const libVersions = (libraries[selectedLib]?.versions || []).map((v) => v.version || v as unknown as string);

  const sampleCode = `import requests

# Simple GET request
response = requests.get("https://api.example.com/users")
users = response.json()

# POST with JSON body
new_user = requests.post(
    "https://api.example.com/users",
    json={"name": "Alice", "email": "alice@example.com"}
)

# Using a session
session = requests.Session()
session.headers.update({"Authorization": "Bearer token123"})
resp = session.get("https://api.example.com/me")
print(resp.json())

# DELETE request
requests.delete("https://api.example.com/users/123")`;

  const handlePreview = async () => {
    if (!sourceCode.trim()) { setError("Enter some code to migrate"); return; }
    setLoading(true);
    setError("");
    setPreview(null);
    setResult(null);
    try {
      const libs = await api.libraries.list();
      const libData = libs.libraries[selectedLib];
      if (!libData) { setError("Select a library"); setLoading(false); return; }
      const libDetail = await api.libraries.get(selectedLib);
      const allRules = libDetail.versions?.flatMap((v: { rules: unknown[] }) => v.rules) || [];
      const data = await api.preview(sourceCode, allRules, sourceVersion || undefined, targetVersion || undefined);
      setPreview(data);
      setActiveTab("preview");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Preview failed");
    }
    setLoading(false);
  };

  const handleMigrate = async () => {
    if (!sourceCode.trim()) { setError("Enter some code to migrate"); return; }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const libDetail = await api.libraries.get(selectedLib);
      const allRules = libDetail.versions?.flatMap((v: { rules: unknown[] }) => v.rules) || [];
      const data = await api.migrate(sourceCode, allRules, sourceVersion || undefined, targetVersion || undefined);
      setResult(data);
      setActiveTab("result");
      const migrations = JSON.parse(localStorage.getItem("mg_migration_history") || "[]");
      migrations.unshift({ code: sourceCode, result: data, timestamp: Date.now(), library: selectedLib });
      if (migrations.length > 50) migrations.pop();
      localStorage.setItem("mg_migration_history", JSON.stringify(migrations));
      const count = parseInt(localStorage.getItem("mg_migrations") || "0") + 1;
      localStorage.setItem("mg_migrations", count.toString());
      localStorage.setItem("mg_last_run", new Date().toISOString());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Migration failed");
    }
    setLoading(false);
  };

  const copyResult = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="animate-fade-up">
      <div className="mb-8">
        <h1 className="text-[28px] font-bold text-zinc-100 tracking-tight">New Migration</h1>
        <p className="text-[14px] text-zinc-400 mt-1">Paste code, select a library, and transform it</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Source code + settings */}
        <div className="space-y-4">
          {/* Library selection */}
          <div className="bg-[#18181b] rounded-xl border border-white/10 p-5">
            <label className="block text-[13px] font-semibold text-zinc-300 mb-2">Migration Library</label>
            <select value={selectedLib} onChange={(e) => { setSelectedLib(e.target.value); setSourceVersion(""); setTargetVersion(""); }}
              className="w-full px-3.5 py-2.5 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all">
              <option value="">Select a library...</option>
              {Object.entries(libraries).map(([name, info]) => (
                <option key={name} value={name}>{name} ({info.rule_count} rules) [{info.source}]</option>
              ))}
            </select>
            <div className="grid grid-cols-2 gap-3 mt-3">
              <div>
                <label className="block text-[12px] font-semibold text-zinc-400 mb-1.5">Source version</label>
                <select value={sourceVersion} onChange={(e) => setSourceVersion(e.target.value)}
                  className="w-full px-3 py-2 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all">
                  <option value="">Any version</option>
                  {libVersions.map((v) => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[12px] font-semibold text-zinc-400 mb-1.5">Target version</label>
                <select value={targetVersion} onChange={(e) => setTargetVersion(e.target.value)}
                  className="w-full px-3 py-2 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all">
                  <option value="">Latest</option>
                  {libVersions.map((v) => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
            </div>
          </div>

          {/* Source code */}
          <div className="bg-[#18181b] rounded-xl border border-white/10 p-5">
            <div className="flex items-center justify-between mb-3">
              <label className="text-[13px] font-semibold text-zinc-300">Source Code</label>
              <button onClick={() => setSourceCode(sampleCode)}
                className="text-[12px] text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1 transition-colors">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
                Load sample
              </button>
            </div>
            <textarea
              value={sourceCode}
              onChange={(e) => setSourceCode(e.target.value)}
              placeholder="Paste your Python code here..."
              className="w-full h-72 px-4 py-3 bg-[#09090b] border border-white/10 rounded-xl text-[13px] text-zinc-100 font-mono placeholder-zinc-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all resize-none"
              spellCheck={false}
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button onClick={handlePreview} disabled={loading || !sourceCode.trim()}
              className="flex-1 border border-white/10 text-zinc-300 px-4 py-3 rounded-xl text-[13px] font-semibold hover:bg-white/5 disabled:opacity-50 transition-all btn-press">
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                  Processing...
                </span>
              ) : "Preview Diff"}
            </button>
            <button onClick={handleMigrate} disabled={loading || !sourceCode.trim()}
              className="flex-1 bg-blue-600 text-white px-4 py-3 rounded-xl text-[13px] font-semibold hover:bg-blue-700 disabled:opacity-50 transition-all btn-press">
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                  Processing...
                </span>
              ) : "Apply Migration"}
            </button>
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3.5 text-[13px] text-red-400 flex items-center gap-2">
              <svg className="w-4 h-4 text-red-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {error}
            </div>
          )}
        </div>

        {/* Right: Preview / Result */}
        <div>
          {(preview || result) && (
            <div className="bg-[#18181b] rounded-xl border border-white/10 overflow-hidden">
              <div className="flex border-b border-white/10">
                <button onClick={() => setActiveTab("preview")}
                  className={`flex-1 px-5 py-3.5 text-[13px] font-semibold transition-all ${
                    activeTab === "preview" ? "text-zinc-100 border-b-2 border-blue-500 bg-white/5" : "text-zinc-500 hover:text-zinc-300"
                  }`}>
                  Diff Preview
                </button>
                <button onClick={() => setActiveTab("result")}
                  className={`flex-1 px-5 py-3.5 text-[13px] font-semibold transition-all ${
                    activeTab === "result" ? "text-zinc-100 border-b-2 border-blue-500 bg-white/5" : "text-zinc-500 hover:text-zinc-300"
                  }`}>
                  Transformed Code
                </button>
              </div>

              <div className="p-5">
                {activeTab === "preview" && preview && (
                  <div>
                    <div className="flex items-center gap-5 mb-5">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-blue-500" />
                        <span className="text-[13px] text-zinc-400">
                          <span className="font-bold text-zinc-100">{preview.change_count}</span> changes detected
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-emerald-400" />
                        <span className="text-[13px] text-zinc-400">
                          <span className="font-bold text-zinc-100">{Math.round(preview.average_confidence * 100)}%</span> avg confidence
                        </span>
                      </div>
                    </div>
                    {preview.changes.length > 0 ? (
                      <div className="space-y-2">
                        {preview.changes.map((change, i) => (
                          <div key={i} className="flex items-start gap-3 p-3 bg-[#09090b] rounded-xl border border-white/10">
                            <svg className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                            </svg>
                            <span className="text-[13px] text-zinc-300">{change}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-[13px] text-zinc-500 py-6 text-center">No changes detected</p>
                    )}
                  </div>
                )}

                {activeTab === "result" && (result || preview?.transformed_code) && (
                  <div className="relative">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-[12px] font-semibold text-zinc-400">Transformed code</span>
                      <button
                        onClick={() => copyResult(result?.transformed_code || preview?.transformed_code || "")}
                        className="text-[12px] text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1.5 transition-colors"
                      >
                        {copied ? (
                          <>
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                            </svg>
                            Copied!
                          </>
                        ) : (
                          <>
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                            </svg>
                            Copy
                          </>
                        )}
                      </button>
                    </div>
                    <pre className="bg-[#09090b] border border-white/10 rounded-xl p-4 text-[12px] text-zinc-400 font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed">
                      {result?.transformed_code || preview?.transformed_code}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}

          {!preview && !result && !loading && (
            <div className="bg-[#18181b] rounded-xl border border-white/10 p-16 text-center">
              <div className="w-16 h-16 rounded-2xl bg-[#09090b] flex items-center justify-center mx-auto mb-5">
                <svg className="w-8 h-8 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
                </svg>
              </div>
              <p className="text-[15px] font-semibold text-zinc-100 mb-1">No output yet</p>
              <p className="text-[13px] text-zinc-400">Paste code and click Preview or Apply Migration</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function NewMigrationPage() {
  return (
    <Suspense fallback={
      <div className="space-y-6 animate-fade-in">
        <div className="space-y-3">
          <div className="h-8 skeleton w-1/3" />
          <div className="h-4 skeleton w-2/3" />
        </div>
        <div className="grid grid-cols-2 gap-6">
          <div className="h-96 skeleton rounded-xl" />
          <div className="h-96 skeleton rounded-xl" />
        </div>
      </div>
    }>
      <NewMigrationContent />
    </Suspense>
  );
}
