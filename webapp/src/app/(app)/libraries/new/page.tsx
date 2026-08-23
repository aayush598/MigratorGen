"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Check } from "lucide-react";
import { client } from "@/lib/api-client";
import { usePackBuilderStore } from "@/stores/pack-builder-store";
import { toast } from "@/stores/ui-store";
import { Button } from "@/components/ui/button";
import { DetailsStep } from "@/components/rules/details-step";
import { VersionsStep } from "@/components/rules/versions-step";
import { RulesStep } from "@/components/rules/rules-step";

type Step = "details" | "versions" | "rules";

export default function NewLibraryPage() {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [publishAfterSave, setPublishAfterSave] = useState(false);

  const step = usePackBuilderStore((s) => s.step);
  const setStep = usePackBuilderStore((s) => s.setStep);
  const reset = usePackBuilderStore((s) => s.reset);
  const name = usePackBuilderStore((s) => s.name);
  const library = usePackBuilderStore((s) => s.library);
  const versions = usePackBuilderStore((s) => s.versions);
  const editingPackId = usePackBuilderStore((s) => s.editingPackId);

  const onSave = async () => {
    if (!name || !library) {
      toast.error("Complete the pack details first");
      setStep("details");
      return;
    }
    const totalRules = versions.reduce((sum, v) => sum + v.rules.length, 0);
    if (totalRules === 0) {
      toast.error("Add at least one rule");
      setStep("rules");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name,
        description: usePackBuilderStore.getState().description,
        library,
        versions: versions.map((v) => ({
          version: v.version,
          release_date: v.release_date || null,
          notes: v.notes || null,
          rules: v.rules.map((r) => ({
            ...r,
            id: r.id || `${library.toUpperCase().replace(/[^A-Z0-9]/g, "") || "RULE"}-${v.version}-${r.change_type}`,
            version_introduced: v.version,
          })),
        })),
      };
      if (editingPackId) {
        await client.current.packs.update(editingPackId, payload);
        if (publishAfterSave) await client.current.packs.publish(editingPackId);
        toast.success("Pack updated");
      } else {
        const created = await client.current.packs.create(payload);
        if (publishAfterSave) await client.current.packs.publish(created.id);
        toast.success(publishAfterSave ? "Pack created and published" : "Pack created");
      }
      reset();
      router.push(`/libraries/${encodeURIComponent(library)}`);
      router.refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : editingPackId ? "Failed to update pack" : "Failed to save pack");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="animate-fade-up">
      <div className="mb-8">
        <Link href="/libraries" className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 transition-colors hover:text-slate-900">
          <ArrowLeft className="h-3 w-3" /> All libraries
        </Link>
        <h1 className="mt-3 text-[28px] font-bold tracking-tight text-slate-900">
          {editingPackId ? "Edit migration pack" : "Create migration pack"}
        </h1>
        <p className="mt-1 text-sm text-slate-500">Define versions and rules for a custom library migration.</p>
      </div>

      <div className="mb-6 flex items-center gap-2">
        {(["details", "versions", "rules"] as Step[]).map((s, i) => (
          <button
            key={s}
            type="button"
            onClick={() => setStep(s)}
            className={`btn-press flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-medium capitalize transition-colors ${
              step === s
                ? "border-slate-900 bg-slate-900 text-white"
                : "border-slate-200 bg-white text-slate-500 hover:border-slate-300"
            }`}
          >
            <span
              className={`flex h-4 w-4 items-center justify-center rounded-full text-[10px] ${
                step === s ? "bg-white/20" : "bg-slate-100"
              }`}
            >
              {i + 1}
            </span>
            {s}
            <Check className={`h-3 w-3 ${step !== s && isComplete(s) ? "text-emerald-500" : "hidden"}`} />
          </button>
        ))}
      </div>

      {step === "details" && <DetailsStep onNext={() => setStep("versions")} isEditing={Boolean(editingPackId)} />}
      {step === "versions" && <VersionsStep onBack={() => setStep("details")} onNext={() => setStep("rules")} />}
      {step === "rules" && (
        <RulesStep
          saving={saving}
          publishAfterSave={publishAfterSave}
          onPublishChange={setPublishAfterSave}
          onBack={() => setStep("versions")}
          onSave={onSave}
        />
      )}
    </div>
  );
}

function isComplete(step: Step): boolean {
  const s = usePackBuilderStore.getState();
  if (step === "details") return Boolean(s.name && s.library);
  if (step === "versions") return s.versions.length > 0;
  return false;
}
