"use client";

import { create } from "zustand";

export interface RuleDraft {
  id: string;
  change_type: string;
  description: string;
  old_name: string;
  new_name: string;
  function_name: string;
  argument_name: string;
  new_argument_name: string;
  replacement: string;
  safety: "safe" | "review_required" | "risky";
  confidence_hint: string;
  tags: string[];
}

export interface VersionDraft {
  version: string;
  release_date: string;
  notes: string;
  rules: RuleDraft[];
}

interface PackBuilderState {
  step: "details" | "versions" | "rules";
  name: string;
  description: string;
  library: string;
  versions: VersionDraft[];
  selectedVersionIndex: number;
  editingRuleIndex: number | null;
  editingPackId: string | null;
  setStep: (step: PackBuilderState["step"]) => void;
  setDetails: (details: { name: string; description: string; library: string }) => void;
  addVersion: () => void;
  removeVersion: (index: number) => void;
  updateVersion: (index: number, patch: Partial<VersionDraft>) => void;
  selectVersion: (index: number) => void;
  addRule: (versionIndex: number, rule: RuleDraft) => void;
  updateRule: (versionIndex: number, ruleIndex: number, rule: Partial<RuleDraft>) => void;
  removeRule: (versionIndex: number, ruleIndex: number) => void;
  setEditingRule: (index: number | null) => void;
  loadForEdit: (pack: {
    id: string;
    name: string;
    description?: string;
    library: string;
    versions: { version: string; release_date?: string | null; notes?: string | null; rules: RuleDraft[] }[];
  }) => void;
  reset: () => void;
}

export function emptyRule(): RuleDraft {
  return {
    id: "",
    change_type: "rename_function",
    description: "",
    old_name: "",
    new_name: "",
    function_name: "",
    argument_name: "",
    new_argument_name: "",
    replacement: "",
    safety: "safe",
    confidence_hint: "high",
    tags: [],
  };
}

const initialVersions = (): VersionDraft[] => [
  { version: "0.1.0", release_date: "", notes: "", rules: [] },
];

export const usePackBuilderStore = create<PackBuilderState>((set) => ({
  step: "details",
  name: "",
  description: "",
  library: "",
  versions: initialVersions(),
  selectedVersionIndex: 0,
  editingRuleIndex: null,
  editingPackId: null,
  setStep: (step) => set({ step }),
  setDetails: (details) =>
    set({
      name: details.name,
      description: details.description,
      library: details.library,
      versions: initialVersions(),
      selectedVersionIndex: 0,
      step: "versions",
    }),
  addVersion: () =>
    set((s) => ({
      versions: [...s.versions, { version: `0.${s.versions.length + 1}.0`, release_date: "", notes: "", rules: [] }],
      selectedVersionIndex: s.versions.length,
    })),
  removeVersion: (index) =>
    set((s) => {
      if (s.versions.length <= 1) return {};
      const versions = s.versions.filter((_, i) => i !== index);
      return { versions, selectedVersionIndex: Math.min(s.selectedVersionIndex, versions.length - 1) };
    }),
  updateVersion: (index, patch) =>
    set((s) => ({
      versions: s.versions.map((v, i) => (i === index ? { ...v, ...patch } : v)),
    })),
  selectVersion: (index) => set({ selectedVersionIndex: index }),
  addRule: (versionIndex, rule) =>
    set((s) => ({
      versions: s.versions.map((v, i) =>
        i === versionIndex ? { ...v, rules: [...v.rules, { ...rule }] } : v,
      ),
      editingRuleIndex: null,
    })),
  updateRule: (versionIndex, ruleIndex, rule) =>
    set((s) => ({
      versions: s.versions.map((v, i) =>
        i === versionIndex
          ? { ...v, rules: v.rules.map((r, j) => (j === ruleIndex ? { ...r, ...rule } : r)) }
          : v,
      ),
    })),
  removeRule: (versionIndex, ruleIndex) =>
    set((s) => ({
      versions: s.versions.map((v, i) =>
        i === versionIndex ? { ...v, rules: v.rules.filter((_, j) => j !== ruleIndex) } : v,
      ),
    })),
  setEditingRule: (index) => set({ editingRuleIndex: index }),
  loadForEdit: (pack) =>
    set({
      step: "details",
      editingPackId: pack.id,
      name: pack.name,
      description: pack.description ?? "",
      library: pack.library,
      versions:
        pack.versions.length > 0
          ? pack.versions.map((v) => ({
              version: v.version,
              release_date: v.release_date ?? "",
              notes: v.notes ?? "",
              rules: (v.rules ?? []).map((r) => ({ ...r })),
            }))
          : initialVersions(),
      selectedVersionIndex: 0,
      editingRuleIndex: null,
    }),
  reset: () =>
    set({
      step: "details",
      name: "",
      description: "",
      library: "",
      versions: initialVersions(),
      selectedVersionIndex: 0,
      editingRuleIndex: null,
      editingPackId: null,
    }),
}));
