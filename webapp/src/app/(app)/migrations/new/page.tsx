"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Check, Copy, Eye, Wand2, ArrowRight, AlertCircle } from "lucide-react";
import { client } from "@/lib/api-client";
import type { DiffPreview, MigrateResponse } from "@/schemas";
import { migrationFormSchema, type MigrationFormInput } from "@/schemas";
import { useMigrationStore } from "@/stores/migration-store";
import { toast } from "@/stores/ui-store";
import { Button } from "@/components/ui/button";
import { Select, Textarea, Label, FieldError } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { SideBySideDiff } from "@/components/diff/side-by-side-diff";

const SAMPLE_CODE = `# fetch_users.py
import requests

BASE_URL = "https://api.acme.dev"

def fetch_users():
    session = requests.Session()
    resp = session.get(BASE_URL)
    return resp.json()["users"]`;

function NewMigrationInner() {
  const searchParams = useSearchParams();
  const presetLibrary = searchParams.get("library") ?? "";
  const addRun = useMigrationStore((s) => s.addRun);

  const [libraries, setLibraries] = useState<Record<string, { rule_count: number; source: string; versions?: { version: string; rules: unknown[] }[] }>>({});
  const [preview, setPreview] = useState<DiffPreview | null>(null);
  const [result, setResult] = useState<MigrateResponse | null>(null);
  const [busy, setBusy] = useState<"preview" | "apply" | null>(null);
  const [activeTab, setActiveTab] = useState<"preview" | "result">("preview");
  const [copied, setCopied] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<MigrationFormInput>({
    resolver: zodResolver(migrationFormSchema),
    defaultValues: {
      sourceCode: SAMPLE_CODE,
      library: presetLibrary,
      sourceVersion: "",
      targetVersion: "",
    },
  });

  useEffect(() => {
    client.current.libraries.list().then(setLibraries).catch(() => {});
  }, []);

  useEffect(() => {
    if (presetLibrary) setValue("library", presetLibrary);
  }, [presetLibrary, setValue]);

  const selectedLib = watch("library");
  const sourceCode = watch("sourceCode");
  const sourceVersion = watch("sourceVersion");
  const targetVersion = watch("targetVersion");

  async function collectRules(): Promise<{ rules: unknown[] }> {
    if (!selectedLib) return { rules: [] };
    const libDetail = await client.current.libraries.get(selectedLib);
    const allRules: unknown[] = [];
    for (const v of libDetail.versions ?? []) {
      for (const r of v.rules ?? []) allRules.push(r);
    }
    return { rules: allRules };
  }

  const onPreview = handleSubmit(async (data) => {
    setBusy("preview");
    setPreview(null);
    setResult(null);
    try {
      const { rules } = await collectRules();
      const res = await client.current.preview(data.sourceCode, rules, {
        sourceVersion: data.sourceVersion || undefined,
        targetVersion: data.targetVersion || undefined,
      });
      setPreview(res);
      setActiveTab("preview");
      toast.success(`Preview ready — ${res.change_count} change(s) found`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setBusy(null);
    }
  });

  const onApply = handleSubmit(async (data) => {
    setBusy("apply");
    try {
      const { rules } = await collectRules();
      const res = await client.current.migrate(data.sourceCode, rules, {
        sourceVersion: data.sourceVersion || undefined,
        targetVersion: data.targetVersion || undefined,
      });
      setResult(res);
      setActiveTab("result");
      addRun({
        library: data.library,
        sourceVersion: data.sourceVersion ?? "",
        targetVersion: data.targetVersion ?? "",
        changeCount: res.changes.length,
        wasModified: res.was_modified,
        sourceCode: res.original_code,
        transformedCode: res.transformed_code,
      });
      toast.success(res.was_modified ? "Migration applied" : "No changes were needed");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Migration failed");
    } finally {
      setBusy(null);
    }
  });

  const shownCode = activeTab === "result" ? (result?.transformed_code ?? "") : (preview?.transformed_code ?? sourceCode);

  function handleCopy() {
    navigator.clipboard.writeText(shownCode).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <div className="animate-fade-up">
      <div className="mb-8">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Link href="/migrations" className="transition-colors hover:text-slate-900">Migrations</Link>
          <span>/</span>
          <span className="text-slate-600">New migration</span>
        </div>
        <h1 className="mt-1.5 text-[28px] font-bold tracking-tight text-slate-900">New migration</h1>
        <p className="mt-1 text-sm text-slate-500">Paste your Python code, pick a pack and preview the transformation.</p>
      </div>

      <form onSubmit={(e) => e.preventDefault()} className="grid grid-cols-1 gap-6 lg:grid-cols-[340px_1fr]">
        <div className="space-y-5">
          <Card className="p-5">
            <Label htmlFor="library">Library pack</Label>
            <Select id="library" {...register("library")} error={errors.library?.message}>
              <option value="">Select a library…</option>
              {Object.entries(libraries).map(([name, lib]) => (
                <option key={name} value={name}>
                  {name} ({lib.rule_count} rules)
                </option>
              ))}
            </Select>
            <FieldError message={errors.library?.message} />

            <div className="mt-4 grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="sourceVersion">From version</Label>
                <Select id="sourceVersion" {...register("sourceVersion")}>
                  <option value="">Default</option>
                </Select>
              </div>
              <div>
                <Label htmlFor="targetVersion">To version</Label>
                <Select id="targetVersion" {...register("targetVersion")}>
                  <option value="">Latest</option>
                  {(libraries[selectedLib]?.versions ?? []).map((v) => (
                    <option key={v.version} value={v.version}>v{v.version}</option>
                  ))}
                </Select>
              </div>
            </div>

            <div className="mt-4">
              <Label htmlFor="sourceCode">Source code</Label>
              <Textarea
                id="sourceCode"
                rows={12}
                spellCheck={false}
                placeholder="Paste your Python code here…"
                {...register("sourceCode")}
              />
              <FieldError message={errors.sourceCode?.message} />
            </div>

            <div className="mt-5 flex flex-col gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={onPreview}
                loading={busy === "preview"}
                disabled={!sourceCode}
              >
                <Eye className="h-3.5 w-3.5" />
                Preview changes
              </Button>
              <Button type="button" onClick={onApply} loading={busy === "apply"} disabled={!sourceCode}>
                <Wand2 className="h-3.5 w-3.5" />
                Apply migration
              </Button>
            </div>
          </Card>
        </div>

        <Card className="min-h-[520px] overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5">
            <div className="flex items-center gap-1 rounded-lg bg-slate-100 p-0.5">
              <button
                type="button"
                onClick={() => setActiveTab("preview")}
                className={`btn-press rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  activeTab === "preview" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"
                }`}
              >
                Preview {preview && `· ${preview.change_count}`}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("result")}
                disabled={!result}
                className={`btn-press rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-40 ${
                  activeTab === "result" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"
                }`}
              >
                Result
              </button>
            </div>
            <Button type="button" variant="ghost" size="sm" onClick={handleCopy} disabled={!shownCode}>
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? "Copied" : "Copy"}
            </Button>
          </div>

          <div className="p-4">
            {!preview && !result && (
              <div className="flex h-[420px] flex-col items-center justify-center text-center">
                <AlertCircle className="h-10 w-10 text-slate-200" />
                <p className="mt-4 text-sm font-medium text-slate-400">Nothing to show yet</p>
                <p className="mt-1 max-w-xs text-xs leading-relaxed text-slate-300">
                  Configure your migration on the left and hit “Preview changes”.
                </p>
              </div>
            )}

            {activeTab === "preview" && preview && (
              <div>
                {preview.original_code || preview.transformed_code ? (
                  <SideBySideDiff
                    original={preview.original_code ?? ""}
                    transformed={preview.transformed_code ?? ""}
                  />
                ) : null}
                {!preview.diff ? (
                  <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center">
                    <p className="text-sm font-medium text-slate-500">No differences detected</p>
                    <p className="mt-1 text-xs text-slate-400">Your code is already compatible with the target version.</p>
                  </div>
                ) : null}
                {preview.change_count > 0 && (
                  <div className="mt-3 flex items-center justify-between rounded-lg bg-emerald-50 px-4 py-2.5 text-xs text-emerald-700">
                    <span>{preview.change_count} change(s) · avg confidence {(preview.average_confidence * 100).toFixed(0)}%</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </div>
                )}
              </div>
            )}

            {activeTab === "result" && result && (
              <pre className="code-input whitespace-pre-wrap rounded-xl bg-slate-50 p-4 text-xs leading-relaxed text-slate-700">
                {result.transformed_code}
              </pre>
            )}
          </div>
        </Card>
      </form>
    </div>
  );
}

export default function NewMigrationPage() {
  return (
    <Suspense fallback={<div className="skeleton h-96 w-full" />}>
      <NewMigrationInner />
    </Suspense>
  );
}
