"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

const CHANGE_TYPES = [
  { value: "rename_import", label: "Rename import", desc: "Rewrite import statements" },
  { value: "rename_function", label: "Rename function", desc: "Rename function calls (supports dotted names like requests.get)" },
  { value: "rename_class", label: "Rename class", desc: "Rename class references" },
  { value: "rename_attribute", label: "Rename attribute", desc: "Rename attribute access" },
  { value: "add_argument", label: "Add argument", desc: "Add argument to function call" },
  { value: "remove_argument", label: "Remove argument", desc: "Remove argument from call" },
  { value: "move_to_module", label: "Move to module", desc: "Move symbol between modules" },
  { value: "deprecate_function", label: "Deprecate function", desc: "Mark function as deprecated" },
];

interface RuleDraft {
  _key: number;
  id: string;
  change_type: string;
  description: string;
  old_name: string;
  new_name: string;
  old_module: string;
  new_module: string;
  function_name: string;
  argument_name: string;
  replacement: string;
  safety: string;
  confidence_hint: string;
  tags: string;
}

interface VersionDraft {
  version: string;
  release_date: string;
  rules: RuleDraft[];
}

let nextKey = 1;
function newRule(): RuleDraft {
  return {
    _key: nextKey++,
    id: "",
    change_type: "rename_function",
    description: "",
    old_name: "",
    new_name: "",
    old_module: "",
    new_module: "",
    function_name: "",
    argument_name: "",
    replacement: "",
    safety: "review_required",
    confidence_hint: "high",
    tags: "",
  };
}

function newVersion(): VersionDraft {
  return { version: "", release_date: "", rules: [newRule()] };
}

export default function NewLibraryPage() {
  const router = useRouter();
  const [step, setStep] = useState<"details" | "versions" | "rules">("details");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [librarySlug, setLibrarySlug] = useState("");
  const [versions, setVersions] = useState<VersionDraft[]>([{ version: "0.1.0", release_date: "", rules: [newRule()] }]);
  const [selectedVersion, setSelectedVersion] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [editingRule, setEditingRule] = useState<number | null>(null);

  const currentVersion = versions[selectedVersion];
  const currentRules = currentVersion?.rules || [];

  const updateVersion = (idx: number, field: keyof VersionDraft, value: string) => {
    setVersions((prev) => prev.map((v, i) => (i === idx ? { ...v, [field]: value } : v)));
  };

  const updateRule = (ruleIdx: number, field: keyof RuleDraft, value: string) => {
    setVersions((prev) =>
      prev.map((v, vi) =>
        vi === selectedVersion
          ? { ...v, rules: v.rules.map((r, ri) => (ri === ruleIdx ? { ...r, [field]: value } : r)) }
          : v
      )
    );
  };

  const addRule = () => {
    setVersions((prev) =>
      prev.map((v, i) => (i === selectedVersion ? { ...v, rules: [...v.rules, newRule()] } : v))
    );
  };

  const removeRule = (ruleIdx: number) => {
    setVersions((prev) =>
      prev.map((v, i) =>
        i === selectedVersion ? { ...v, rules: v.rules.filter((_, ri) => ri !== ruleIdx) } : v
      )
    );
    setEditingRule(null);
  };

  const addVersion = () => {
    setVersions((prev) => [...prev, newVersion()]);
    setSelectedVersion(versions.length);
  };

  const removeVersion = (idx: number) => {
    if (versions.length <= 1) return;
    setVersions((prev) => prev.filter((_, i) => i !== idx));
    setSelectedVersion(Math.min(selectedVersion, versions.length - 2));
  };

  const canProceedDetails = name.trim() && librarySlug.trim();
  const canProceedVersions = versions.every((v) => v.version.trim());

  const handleSave = async (publish: boolean) => {
    if (!canProceedDetails || !canProceedVersions) {
      setError("Please fill in all required fields");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const versionsData = versions.map((v) => ({
        version: v.version,
        release_date: v.release_date || null,
        rules: v.rules
          .filter((r) => r.description || r.old_name || r.new_name)
          .map((r) => ({
            id: r.id || `${librarySlug}-${Math.random().toString(36).slice(2, 8)}`,
            change_type: r.change_type,
            description: r.description || `${r.change_type}: ${r.old_name} -> ${r.new_name}`,
            version_introduced: v.version,
            old_name: r.old_name || null,
            new_name: r.new_name || null,
            old_module: r.old_module || null,
            new_module: r.new_module || null,
            function_name: r.function_name || null,
            argument_name: r.argument_name || null,
            replacement: r.replacement || null,
            safety: r.safety,
            confidence_hint: r.confidence_hint,
            tags: r.tags ? r.tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
          })),
      }));

      const result = await api.userPacks.create({ name, description, library: librarySlug, versions: versionsData });
      if (publish) await api.userPacks.publish(result.id);
      router.push(`/libraries/${result.id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create library");
      setSaving(false);
    }
  };

  const getChangeTypeFields = (ct: string) => {
    switch (ct) {
      case "rename_import": return { showModule: true, showFunc: false, showArg: false };
      case "rename_function": return { showModule: false, showFunc: false, showArg: false };
      case "rename_class": return { showModule: false, showFunc: false, showArg: false };
      case "rename_attribute": return { showModule: false, showFunc: false, showArg: false };
      case "add_argument": return { showModule: false, showFunc: true, showArg: true };
      case "remove_argument": return { showModule: false, showFunc: true, showArg: true };
      case "move_to_module": return { showModule: true, showFunc: false, showArg: false };
      case "deprecate_function": return { showModule: false, showFunc: false, showArg: false };
      default: return { showModule: false, showFunc: false, showArg: false };
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Create Library</h1>
        <p className="text-sm text-gray-500 mt-1">Define a custom migration library with versions and rules</p>
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-2 mb-8">
        {(["details", "versions", "rules"] as const).map((s, i) => {
          const active = step === s;
          const completed = (s === "details" && canProceedDetails) || (s === "versions" && canProceedVersions && canProceedDetails);
          return (
            <button key={s} onClick={() => setStep(s)} className="flex items-center gap-2 group">
              <span className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold transition-colors ${
                active ? "bg-blue-600 text-white" : completed ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-400"
              }`}>
                {completed && !active ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : i + 1}
              </span>
              <span className={`text-sm font-medium ${active ? "text-blue-700" : completed ? "text-gray-700" : "text-gray-400"}`}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </span>
              {i < 2 && <div className={`w-8 h-px ${completed ? "bg-blue-300" : "bg-gray-200"}`} />}
            </button>
          );
        })}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-center gap-3">
          <svg className="w-5 h-5 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Step 1: Details */}
      {step === "details" && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-5">Library Details</h2>
          <div className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Name <span className="text-red-400">*</span></label>
              <input
                type="text" value={name} onChange={(e) => setName(e.target.value)}
                placeholder="e.g. requests to httpx"
                className="w-full px-3 py-2.5 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Slug <span className="text-red-400">*</span></label>
              <input
                type="text" value={librarySlug}
                onChange={(e) => setLibrarySlug(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""))}
                placeholder="e.g. requests-to-httpx"
                className="w-full px-3 py-2.5 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
              <p className="text-xs text-gray-400 mt-1">Lowercase, hyphens allowed. Used in CLI commands.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Description</label>
              <textarea
                value={description} onChange={(e) => setDescription(e.target.value)}
                placeholder="What does this library migrate?"
                rows={3}
                className="w-full px-3 py-2.5 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none"
              />
            </div>
            <div className="flex justify-end">
              <button onClick={() => setStep("versions")} disabled={!canProceedDetails}
                className="bg-blue-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
                Next: Versions
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Versions */}
      {step === "versions" && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold text-gray-900">Versions</h2>
            <button onClick={addVersion} className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Add version
            </button>
          </div>
          <p className="text-sm text-gray-500 mb-5">Define the versions your library supports. Users migrate between these versions.</p>
          <div className="space-y-3">
            {versions.map((v, idx) => (
              <div key={idx} className={`flex items-center gap-3 p-4 rounded-lg border transition-colors ${
                idx === selectedVersion ? "border-blue-300 bg-blue-50" : "border-gray-200 hover:border-gray-300"
              }`}>
                <div className="flex-1 grid grid-cols-2 gap-3">
                  <input
                    type="text" value={v.version}
                    onChange={(e) => updateVersion(idx, "version", e.target.value)}
                    placeholder="0.1.0"
                    className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm font-mono text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                  <input
                    type="date" value={v.release_date}
                    onChange={(e) => updateVersion(idx, "release_date", e.target.value)}
                    className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                  />
                </div>
                <span className="text-xs text-gray-500 whitespace-nowrap">{v.rules.length} rules</span>
                {versions.length > 1 && (
                  <button onClick={() => removeVersion(idx)} className="p-1.5 text-gray-400 hover:text-red-500 transition-colors">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>
          <div className="mt-6 flex justify-between">
            <button onClick={() => setStep("details")}
              className="border border-gray-300 text-gray-700 px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
              Back
            </button>
            <button onClick={() => setStep("rules")} disabled={!canProceedVersions}
              className="bg-blue-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
              Next: Rules
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Rules */}
      {step === "rules" && (
        <div>
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Rules</h2>
              <p className="text-sm text-gray-500 mt-0.5">Define migration rules for each version</p>
            </div>
            <div className="flex items-center gap-3">
              <select
                value={selectedVersion}
                onChange={(e) => { setSelectedVersion(parseInt(e.target.value)); setEditingRule(null); }}
                className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              >
                {versions.map((v, idx) => (
                  <option key={idx} value={idx}>Version {v.version || `v${idx + 1}`}</option>
                ))}
              </select>
              <button onClick={addRule}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors flex items-center gap-1.5">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                </svg>
                Add Rule
              </button>
            </div>
          </div>

          {currentRules.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
              <svg className="w-12 h-12 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <p className="text-gray-500 font-medium">No rules yet</p>
              <p className="text-sm text-gray-400 mt-1">Click &quot;Add Rule&quot; to create your first migration rule</p>
            </div>
          ) : (
            <div className="space-y-3">
              {currentRules.map((rule, ruleIdx) => {
                const isEditing = editingRule === ruleIdx;
                const fields = getChangeTypeFields(rule.change_type);
                const ctLabel = CHANGE_TYPES.find((c) => c.value === rule.change_type)?.label || rule.change_type;

                if (!isEditing) {
                  // Collapsed view
                  return (
                    <div key={rule._key} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-4 hover:border-gray-300 transition-colors">
                      <span className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center text-xs font-medium text-gray-500 flex-shrink-0">
                        {ruleIdx + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">{ctLabel}</span>
                          <span className={`text-xs px-1.5 py-0.5 rounded ${
                            rule.safety === "safe" ? "bg-green-50 text-green-700" :
                            rule.safety === "review_required" ? "bg-yellow-50 text-yellow-700" :
                            "bg-red-50 text-red-700"
                          }`}>{rule.safety.replace("_", " ")}</span>
                        </div>
                        <p className="text-sm text-gray-700 mt-1 truncate">{rule.description || "No description"}</p>
                        {(rule.old_name || rule.new_name) && (
                          <p className="text-xs text-gray-400 font-mono mt-0.5 truncate">
                            {rule.old_name || "—"} → {rule.new_name || "—"}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <button onClick={() => setEditingRule(ruleIdx)}
                          className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Edit">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        <button onClick={() => removeRule(ruleIdx)}
                          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="Delete">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  );
                }

                // Expanded/editing view
                return (
                  <div key={rule._key} className="bg-white rounded-xl border-2 border-blue-300 p-5">
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-sm font-semibold text-gray-900">Rule {ruleIdx + 1}</span>
                      <div className="flex items-center gap-2">
                        <button onClick={() => setEditingRule(null)}
                          className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 rounded hover:bg-gray-100 transition-colors">
                          Collapse
                        </button>
                        <button onClick={() => removeRule(ruleIdx)}
                          className="text-xs text-red-500 hover:text-red-700 px-2 py-1 rounded hover:bg-red-50 transition-colors">
                          Delete
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Change type</label>
                        <select value={rule.change_type} onChange={(e) => updateRule(ruleIdx, "change_type", e.target.value)}
                          className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
                          {CHANGE_TYPES.map((ct) => (
                            <option key={ct.value} value={ct.value}>{ct.label}</option>
                          ))}
                        </select>
                        <p className="text-xs text-gray-400 mt-0.5">{CHANGE_TYPES.find((c) => c.value === rule.change_type)?.desc}</p>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
                        <input type="text" value={rule.description} onChange={(e) => updateRule(ruleIdx, "description", e.target.value)}
                          placeholder="What this rule does"
                          className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                      </div>

                      {fields.showModule ? (
                        <>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Old module</label>
                            <input type="text" value={rule.old_module} onChange={(e) => updateRule(ruleIdx, "old_module", e.target.value)}
                              placeholder="e.g. requests"
                              className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">New module</label>
                            <input type="text" value={rule.new_module} onChange={(e) => updateRule(ruleIdx, "new_module", e.target.value)}
                              placeholder="e.g. httpx"
                              className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                          </div>
                        </>
                      ) : (
                        <>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Old name</label>
                            <input type="text" value={rule.old_name} onChange={(e) => updateRule(ruleIdx, "old_name", e.target.value)}
                              placeholder={rule.change_type === "rename_function" ? "e.g. requests.get" : rule.change_type === "rename_class" ? "e.g. requests.Session" : "e.g. old_name"}
                              className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">New name</label>
                            <input type="text" value={rule.new_name} onChange={(e) => updateRule(ruleIdx, "new_name", e.target.value)}
                              placeholder={rule.change_type === "rename_function" ? "e.g. httpx.get" : rule.change_type === "rename_class" ? "e.g. httpx.Client" : "e.g. new_name"}
                              className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                          </div>
                        </>
                      )}

                      {fields.showFunc && (
                        <>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Function name</label>
                            <input type="text" value={rule.function_name} onChange={(e) => updateRule(ruleIdx, "function_name", e.target.value)}
                              placeholder="e.g. BaseModel"
                              className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-600 mb-1">Argument name</label>
                            <input type="text" value={rule.argument_name} onChange={(e) => updateRule(ruleIdx, "argument_name", e.target.value)}
                              placeholder="e.g. field"
                              className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                          </div>
                        </>
                      )}

                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Safety</label>
                        <select value={rule.safety} onChange={(e) => updateRule(ruleIdx, "safety", e.target.value)}
                          className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none">
                          <option value="safe">Safe</option>
                          <option value="review_required">Review required</option>
                          <option value="risky">Risky</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Tags (comma separated)</label>
                        <input type="text" value={rule.tags} onChange={(e) => updateRule(ruleIdx, "tags", e.target.value)}
                          placeholder="e.g. requests, httpx"
                          className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="mt-6 flex justify-between">
            <button onClick={() => setStep("versions")}
              className="border border-gray-300 text-gray-700 px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
              Back
            </button>
            <div className="flex gap-3">
              <button onClick={() => handleSave(false)} disabled={saving}
                className="border border-gray-300 text-gray-700 px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors">
                {saving ? "Saving..." : "Save as draft"}
              </button>
              <button onClick={() => handleSave(true)} disabled={saving}
                className="bg-blue-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
                {saving ? "Saving..." : "Save & publish"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
