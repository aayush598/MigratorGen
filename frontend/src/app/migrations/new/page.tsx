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
      const libs = await api.libraries.list();
      const libDetail = await api.libraries.get(selectedLib);
      const allRules = libDetail.versions?.flatMap((v: { rules: unknown[] }) => v.rules) || [];
      const data = await api.migrate(sourceCode, allRules, sourceVersion || undefined, targetVersion || undefined);
      setResult(data);
      setActiveTab("result");
      // Save to history
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

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">New Migration</h1>
        <p className="text-sm text-gray-500 mt-1">Paste code, select a library, and migrate it</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Source code + settings */}
        <div className="space-y-4">
          {/* Library selection */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Migration Library</label>
            <select value={selectedLib} onChange={(e) => { setSelectedLib(e.target.value); setSourceVersion(""); setTargetVersion(""); }}
              className="w-full px-3 py-2.5 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
              <option value="">Select a library...</option>
              {Object.entries(libraries).map(([name, info]) => (
                <option key={name} value={name}>{name} ({info.rule_count} rules) [{info.source}]</option>
              ))}
            </select>
            <div className="grid grid-cols-2 gap-3 mt-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Source version</label>
                <select value={sourceVersion} onChange={(e) => setSourceVersion(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
                  <option value="">Any version</option>
                  {libVersions.map((v) => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Target version</label>
                <select value={targetVersion} onChange={(e) => setTargetVersion(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
                  <option value="">Latest</option>
                  {libVersions.map((v) => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
            </div>
          </div>

          {/* Source code */}
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700">Source Code</label>
              <button onClick={() => setSourceCode(sampleCode)} className="text-xs text-blue-600 hover:text-blue-700 font-medium">
                Load sample
              </button>
            </div>
            <textarea
              value={sourceCode}
              onChange={(e) => setSourceCode(e.target.value)}
              placeholder="Paste your Python code here..."
              className="w-full h-72 px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-900 font-mono placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
              spellCheck={false}
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button onClick={handlePreview} disabled={loading || !sourceCode.trim()}
              className="flex-1 border border-gray-300 text-gray-700 px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors">
              {loading ? "Processing..." : "Preview Diff"}
            </button>
            <button onClick={handleMigrate} disabled={loading || !sourceCode.trim()}
              className="flex-1 bg-blue-600 text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
              {loading ? "Processing..." : "Apply Migration"}
            </button>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{error}</div>
          )}
        </div>

        {/* Right: Preview / Result */}
        <div>
          {(preview || result) && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="flex border-b border-gray-200">
                <button onClick={() => setActiveTab("preview")}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                    activeTab === "preview" ? "text-blue-700 border-b-2 border-blue-600" : "text-gray-500 hover:text-gray-700"
                  }`}>
                  Diff Preview
                </button>
                <button onClick={() => setActiveTab("result")}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                    activeTab === "result" ? "text-blue-700 border-b-2 border-blue-600" : "text-gray-500 hover:text-gray-700"
                  }`}>
                  Transformed Code
                </button>
              </div>

              <div className="p-4">
                {activeTab === "preview" && preview && (
                  <div>
                    <div className="flex items-center gap-4 mb-4">
                      <span className="text-sm text-gray-600">
                        <span className="font-semibold text-gray-900">{preview.change_count}</span> changes detected
                      </span>
                      <span className="text-sm text-gray-600">
                        <span className="font-semibold text-gray-900">{Math.round(preview.average_confidence * 100)}%</span> avg confidence
                      </span>
                    </div>
                    {preview.changes.length > 0 ? (
                      <div className="space-y-2">
                        {preview.changes.map((change, i) => (
                          <div key={i} className="flex items-start gap-2 p-2 bg-gray-50 rounded-lg">
                            <svg className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                            </svg>
                            <span className="text-sm text-gray-700">{change}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500 py-4 text-center">No changes detected</p>
                    )}
                  </div>
                )}

                {activeTab === "result" && (result || preview?.transformed_code) && (
                  <div className="relative">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-gray-500">Transformed code</span>
                      <button
                        onClick={() => navigator.clipboard.writeText(result?.transformed_code || preview?.transformed_code || "")}
                        className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                        </svg>
                        Copy
                      </button>
                    </div>
                    <pre className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-900 font-mono overflow-x-auto whitespace-pre-wrap">
                      {result?.transformed_code || preview?.transformed_code}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}

          {!preview && !result && !loading && (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
              <svg className="w-12 h-12 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              <p className="text-gray-500 font-medium">No output yet</p>
              <p className="text-sm text-gray-400 mt-1">Paste code and click Preview or Apply Migration</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function NewMigrationPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64"><div className="text-sm text-gray-500">Loading...</div></div>}>
      <NewMigrationContent />
    </Suspense>
  );
}
