"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

const CHANGE_TYPES = [
  { value: "rename_import", label: "Rename import", desc: "Rewrite import statements", icon: "M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" },
  { value: "rename_function", label: "Rename function", desc: "Rename function calls", icon: "M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" },
  { value: "rename_class", label: "Rename class", desc: "Rename class references", icon: "M4.26 10.147a60.438 60.438 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" },
  { value: "rename_attribute", label: "Rename attribute", desc: "Rename attribute access", icon: "M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" },
  { value: "add_argument", label: "Add argument", desc: "Add argument to function call", icon: "M12 4.5v15m7.5-7.5h-15" },
  { value: "remove_argument", label: "Remove argument", desc: "Remove argument from call", icon: "M19.5 12h-15" },
  { value: "move_to_module", label: "Move to module", desc: "Move symbol between modules", icon: "M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" },
  { value: "deprecate_function", label: "Deprecate function", desc: "Mark function as deprecated", icon: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" },
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

const STEPS = [
  { key: "details", label: "Details", num: "01" },
  { key: "versions", label: "Versions", num: "02" },
  { key: "rules", label: "Rules", num: "03" },
] as const;

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

  const Input = ({ label, required, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label: string; required?: boolean }) => (
    <div>
      <label className="block text-[13px] font-medium text-zinc-300 mb-1.5">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      <input {...props} className={`w-full px-3.5 py-2.5 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 placeholder-zinc-600 [color-scheme:dark] focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all ${props.className || ""}`} />
    </div>
  );

  return (
    <div className="max-w-3xl mx-auto animate-fade-up">
      <div className="mb-8">
        <h1 className="text-[28px] font-bold text-zinc-100 tracking-tight">Create Library</h1>
        <p className="text-[14px] text-zinc-400 mt-1">Define a custom migration library with versions and rules</p>
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-3 mb-8">
        {STEPS.map((s, i) => {
          const active = step === s.key;
          const completed = (s.key === "details" && canProceedDetails) || (s.key === "versions" && canProceedVersions && canProceedDetails);
          return (
            <button key={s.key} onClick={() => setStep(s.key)} className="flex items-center gap-2.5 group">
              <span className={`w-8 h-8 rounded-lg flex items-center justify-center text-[11px] font-bold transition-all ${
                active ? "bg-blue-600 text-white" : completed ? "bg-emerald-400/10 text-emerald-400 border border-emerald-400/20" : "bg-white/5 text-zinc-500"
              }`}>
                {completed && !active ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : s.num}
              </span>
              <span className={`text-[13px] font-semibold ${active ? "text-zinc-100" : completed ? "text-zinc-400" : "text-zinc-500"}`}>
                {s.label}
              </span>
              {i < 2 && <div className={`w-8 h-[2px] rounded-full ${completed ? "bg-emerald-400/40" : "bg-white/10"}`} />}
            </button>
          );
        })}
      </div>

      {error && (
        <div className="bg-red-400/10 border border-red-400/20 rounded-xl p-4 mb-6 flex items-center gap-3">
          <svg className="w-5 h-5 text-red-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-[13px] text-red-400">{error}</p>
        </div>
      )}

      {/* Step 1: Details */}
      {step === "details" && (
        <div className="bg-[#18181b] rounded-xl border border-white/10 p-6 animate-fade-up">
          <h2 className="text-[16px] font-semibold text-zinc-100 mb-6">Library Details</h2>
          <div className="space-y-5">
            <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. requests to httpx" />
            <Input label="Slug" required value={librarySlug} onChange={(e) => setLibrarySlug(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""))} placeholder="e.g. requests-to-httpx" className="font-mono" />
            <p className="text-[12px] text-zinc-500 -mt-3">Lowercase, hyphens allowed. Used in CLI commands.</p>
            <div>
              <label className="block text-[13px] font-medium text-zinc-300 mb-1.5">Description</label>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What does this library migrate?" rows={3}
                className="w-full px-3.5 py-2.5 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 placeholder-zinc-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all resize-none" />
            </div>
            <div className="flex justify-end pt-2">
              <button onClick={() => setStep("versions")} disabled={!canProceedDetails}
                className="bg-blue-600 text-white px-6 py-2.5 rounded-xl text-[13px] font-semibold hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all btn-press">
                Next: Versions
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Versions */}
      {step === "versions" && (
        <div className="bg-[#18181b] rounded-xl border border-white/10 p-6 animate-fade-up">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-[16px] font-semibold text-zinc-100">Versions</h2>
              <p className="text-[13px] text-zinc-400 mt-0.5">Define the versions your library supports</p>
            </div>
            <button onClick={addVersion} className="text-[13px] text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              Add version
            </button>
          </div>

          <div className="space-y-3">
            {versions.map((v, idx) => (
              <div key={idx} className={`flex items-center gap-3 p-4 rounded-xl border transition-all ${
                idx === selectedVersion ? "border-blue-500/40 bg-blue-500/5" : "border-white/10 hover:border-white/20"
              }`}>
                <div className="flex-1 grid grid-cols-2 gap-3">
                  <Input label="" value={v.version} onChange={(e) => updateVersion(idx, "version", e.target.value)} placeholder="0.1.0" className="font-mono text-[13px]" />
                  <Input label="" type="date" value={v.release_date} onChange={(e) => updateVersion(idx, "release_date", e.target.value)} className="text-[13px]" />
                </div>
                <span className="text-[12px] text-zinc-400 whitespace-nowrap font-medium">{v.rules.length} rules</span>
                {versions.length > 1 && (
                  <button onClick={() => removeVersion(idx)} className="p-2 text-zinc-600 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors">
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
              className="border border-white/10 text-zinc-300 px-5 py-2.5 rounded-xl text-[13px] font-semibold hover:bg-white/5 transition-colors">
              Back
            </button>
            <button onClick={() => setStep("rules")} disabled={!canProceedVersions}
              className="bg-blue-600 text-white px-6 py-2.5 rounded-xl text-[13px] font-semibold hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all btn-press">
              Next: Rules
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Rules */}
      {step === "rules" && (
        <div className="animate-fade-up">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-[16px] font-semibold text-zinc-100">Migration Rules</h2>
              <p className="text-[13px] text-zinc-400 mt-0.5">Define transformations for each version</p>
            </div>
            <div className="flex items-center gap-3">
              <select value={selectedVersion} onChange={(e) => { setSelectedVersion(parseInt(e.target.value)); setEditingRule(null); }}
                className="px-3 py-2 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-300 font-medium focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all">
                {versions.map((v, idx) => (
                  <option key={idx} value={idx}>Version {v.version || `v${idx + 1}`}</option>
                ))}
              </select>
              <button onClick={addRule}
                className="bg-blue-600 text-white px-4 py-2 rounded-xl text-[13px] font-semibold hover:bg-blue-700 transition-all flex items-center gap-1.5 btn-press">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Add Rule
              </button>
            </div>
          </div>

          {currentRules.length === 0 ? (
            <div className="bg-[#18181b] rounded-xl border border-white/10 p-16 text-center">
              <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mx-auto mb-5">
                <svg className="w-8 h-8 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-[15px] font-semibold text-zinc-100 mb-1">No rules yet</p>
              <p className="text-[13px] text-zinc-400">Click &quot;Add Rule&quot; to create your first migration rule</p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {currentRules.map((rule, ruleIdx) => {
                const isEditing = editingRule === ruleIdx;
                const fields = getChangeTypeFields(rule.change_type);
                const ctMeta = CHANGE_TYPES.find((c) => c.value === rule.change_type);
                const ctLabel = ctMeta?.label || rule.change_type;

                if (!isEditing) {
                  return (
                    <div key={rule._key} className="bg-[#18181b] rounded-xl border border-white/10 p-4 flex items-center gap-4 hover:border-white/20 transition-all group">
                      <span className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-[12px] font-bold text-zinc-500 flex-shrink-0">
                        {ruleIdx + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-white/5 text-zinc-400 border border-white/10">{ctLabel}</span>
                          <span className={`text-[11px] font-medium px-2 py-0.5 rounded-md ${
                            rule.safety === "safe" ? "bg-emerald-400/10 text-emerald-400 border border-emerald-400/20" :
                            rule.safety === "review_required" ? "bg-amber-400/10 text-amber-400 border border-amber-400/20" :
                            "bg-red-400/10 text-red-400 border border-red-400/20"
                          }`}>{rule.safety.replace("_", " ")}</span>
                        </div>
                        <p className="text-[13px] text-zinc-300 truncate">{rule.description || "No description"}</p>
                        {(rule.old_name || rule.new_name) && (
                          <p className="font-mono text-[12px] text-zinc-500 mt-0.5 truncate">
                            {rule.old_name || "—"} → {rule.new_name || "—"}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onClick={() => setEditingRule(ruleIdx)}
                          className="p-2 text-zinc-600 hover:text-blue-400 hover:bg-blue-400/10 rounded-lg transition-colors" title="Edit">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125" />
                          </svg>
                        </button>
                        <button onClick={() => removeRule(ruleIdx)}
                          className="p-2 text-zinc-600 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors" title="Delete">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  );
                }

                return (
                  <div key={rule._key} className="bg-[#18181b] rounded-xl border-2 border-blue-500/40 p-5 animate-fade-up">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <span className="w-7 h-7 rounded-lg bg-blue-400/10 flex items-center justify-center text-[12px] font-bold text-blue-400">{ruleIdx + 1}</span>
                        <span className="text-[14px] font-semibold text-zinc-100">Rule {ruleIdx + 1}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button onClick={() => setEditingRule(null)}
                          className="text-[12px] text-zinc-400 hover:text-zinc-200 px-2.5 py-1 rounded-lg hover:bg-white/5 transition-colors font-medium">
                          Collapse
                        </button>
                        <button onClick={() => removeRule(ruleIdx)}
                          className="text-[12px] text-red-400 hover:text-red-300 px-2.5 py-1 rounded-lg hover:bg-red-400/10 transition-colors font-medium">
                          Delete
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[12px] font-semibold text-zinc-400 mb-1.5">Change type</label>
                        <select value={rule.change_type} onChange={(e) => updateRule(ruleIdx, "change_type", e.target.value)}
                          className="w-full px-3 py-2.5 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all">
                          {CHANGE_TYPES.map((ct) => (
                            <option key={ct.value} value={ct.value}>{ct.label}</option>
                          ))}
                        </select>
                        <p className="text-[11px] text-zinc-500 mt-1">{CHANGE_TYPES.find((c) => c.value === rule.change_type)?.desc}</p>
                      </div>
                      <div>
                        <label className="block text-[12px] font-semibold text-zinc-400 mb-1.5">Description</label>
                        <input type="text" value={rule.description} onChange={(e) => updateRule(ruleIdx, "description", e.target.value)}
                          placeholder="What this rule does"
                          className="w-full px-3 py-2.5 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 placeholder-zinc-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all" />
                      </div>

                      {fields.showModule ? (
                        <>
                          <div>
                            <label className="block text-[12px] font-semibold text-zinc-400 mb-1.5">Old module</label>
                            <input type="text" value={rule.old_module} onChange={(e) => updateRule(ruleIdx, "old_module", e.target.value)}
                              placeholder="e.g. requests"
                              className="w-full px-3 py-2.5 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 placeholder-zinc-600 font-mono focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all" />
                          </div>
                          <div>
                            <label className="block text-[12px] font-semibold text-zinc-400 mb-1.5">New module</label>
                            <input type="text" value={rule.new_module} onChange={(e) => updateRule(ruleIdx, "new_module", e.target.value)}
                              placeholder="e.g. httpx"
                              className="w-full px-3 py-2.5 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 placeholder-zinc-600 font-mono focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all" />
                          </div>
                        </>
                      ) : (
                        <>
                          <div>
                            <label className="block text-[12px] font-semibold text-zinc-400 mb-1.5">Old name</label>
                            <input type="text" value={rule.old_name} onChange={(e) => updateRule(ruleIdx, "old_name", e.target.value)}
                              placeholder={rule.change_type === "rename_function" ? "e.g. requests.get" : "e.g. old_name"}
                              className="w-full px-3 py-2.5 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 placeholder-zinc-600 font-mono focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all" />
                          </div>
                          <div>
                            <label className="block text-[12px] font-semibold text-zinc-400 mb-1.5">New name</label>
                            <input type="text" value={rule.new_name} onChange={(e) => updateRule(ruleIdx, "new_name", e.target.value)}
                              placeholder={rule.change_type === "rename_function" ? "e.g. httpx.get" : "e.g. new_name"}
                              className="w-full px-3 py-2.5 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 placeholder-zinc-600 font-mono focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all" />
                          </div>
                        </>
                      )}

                      {fields.showFunc && (
                        <>
                          <div>
                            <label className="block text-[12px] font-semibold text-zinc-400 mb-1.5">Function name</label>
                            <input type="text" value={rule.function_name} onChange={(e) => updateRule(ruleIdx, "function_name", e.target.value)}
                              placeholder="e.g. BaseModel"
                              className="w-full px-3 py-2.5 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 placeholder-zinc-600 font-mono focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all" />
                          </div>
                          <div>
                            <label className="block text-[12px] font-semibold text-zinc-400 mb-1.5">Argument name</label>
                            <input type="text" value={rule.argument_name} onChange={(e) => updateRule(ruleIdx, "argument_name", e.target.value)}
                              placeholder="e.g. field"
                              className="w-full px-3 py-2.5 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 placeholder-zinc-600 font-mono focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all" />
                          </div>
                        </>
                      )}

                      <div>
                        <label className="block text-[12px] font-semibold text-zinc-400 mb-1.5">Safety</label>
                        <select value={rule.safety} onChange={(e) => updateRule(ruleIdx, "safety", e.target.value)}
                          className="w-full px-3 py-2.5 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all">
                          <option value="safe">Safe</option>
                          <option value="review_required">Review required</option>
                          <option value="risky">Risky</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[12px] font-semibold text-zinc-400 mb-1.5">Tags (comma separated)</label>
                        <input type="text" value={rule.tags} onChange={(e) => updateRule(ruleIdx, "tags", e.target.value)}
                          placeholder="e.g. requests, httpx"
                          className="w-full px-3 py-2.5 bg-[#18181b] border border-white/10 rounded-xl text-[13px] text-zinc-100 placeholder-zinc-600 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 outline-none transition-all" />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="mt-6 flex justify-between">
            <button onClick={() => setStep("versions")}
              className="border border-white/10 text-zinc-300 px-5 py-2.5 rounded-xl text-[13px] font-semibold hover:bg-white/5 transition-colors">
              Back
            </button>
            <div className="flex gap-3">
              <button onClick={() => handleSave(false)} disabled={saving}
                className="border border-white/10 text-zinc-300 px-5 py-2.5 rounded-xl text-[13px] font-semibold hover:bg-white/5 disabled:opacity-50 transition-colors btn-press">
                {saving ? "Saving..." : "Save as draft"}
              </button>
              <button onClick={() => handleSave(true)} disabled={saving}
                className="bg-blue-600 text-white px-6 py-2.5 rounded-xl text-[13px] font-semibold hover:bg-blue-700 disabled:opacity-50 transition-all btn-press">
                {saving ? "Saving..." : "Save & publish"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
