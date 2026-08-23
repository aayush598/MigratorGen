"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import useSWR from "swr";
import { Copy, KeyRound, Plus, Trash2, Check } from "lucide-react";
import { client } from "@/lib/api-client";
import type { ApiKey } from "@/schemas";
import { apiKeyCreateSchema, type ApiKeyCreateInput } from "@/schemas";
import { toast } from "@/stores/ui-store";
import { Card, Badge, EmptyState } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, FieldError } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";

export default function ApiKeysPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: keys, isLoading, mutate } = useSWR("keys", () => client.current.keys.list());

  const form = useForm<ApiKeyCreateInput>({
    resolver: zodResolver(apiKeyCreateSchema),
    defaultValues: { name: "", scopes: ["migrate", "read"] },
  });

  const onCreate = form.handleSubmit(async (data) => {
    try {
      const created = await client.current.keys.create(data.name, data.scopes);
      setCreatedKey(created.key ?? "");
      setModalOpen(false);
      form.reset();
      mutate();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create key");
    }
  });

  const onDelete = async (keyId: string) => {
    setDeletingId(keyId);
    try {
      await client.current.keys.delete(keyId);
      toast.success("API key revoked");
      mutate();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to revoke key");
    } finally {
      setDeletingId(null);
    }
  };

  function copyKey() {
    if (!createdKey) return;
    navigator.clipboard.writeText(createdKey).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <div className="animate-fade-up">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-bold tracking-tight text-slate-900">API keys</h1>
          <p className="mt-1 text-sm text-slate-500">Authenticate CLI and CI requests against your workspace.</p>
        </div>
        <Button onClick={() => { setModalOpen(true); setCreatedKey(null); }}>
          <Plus className="h-3.5 w-3.5" /> New API key
        </Button>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[1, 2].map((i) => (
            <div key={i} className="skeleton h-16 rounded-xl" />
          ))}
        </div>
      )}

      {!isLoading && (keys ?? []).length === 0 && (
        <EmptyState
          icon={<KeyRound className="h-5 w-5" />}
          title="No API keys"
          description="Create a key to authenticate the migrator-gen CLI against this workspace."
          action={<Button size="sm" onClick={() => setModalOpen(true)}><Plus className="h-3 w-3" /> Create key</Button>}
        />
      )}

      {(keys ?? []).length > 0 && (
        <Card className="overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs uppercase tracking-wide text-slate-400">
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Prefix</th>
                <th className="px-5 py-3 font-medium">Scopes</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {(keys ?? []).map((key) => (
                <tr key={key.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/60">
                  <td className="px-5 py-3.5 font-medium text-slate-900">{key.name}</td>
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-500">{key.key_prefix}…</td>
                  <td className="px-5 py-3.5">
                    <div className="flex flex-wrap gap-1">
                      {key.scopes.map((scope) => (
                        <Badge key={scope}>{scope}</Badge>
                      ))}
                    </div>
                  </td>
                  <td className="px-5 py-3.5">
                    <Badge tone={key.is_active ? "success" : "danger"}>{key.is_active ? "active" : "revoked"}</Badge>
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <button
                      onClick={() => onDelete(key.id)}
                      disabled={deletingId === key.id}
                      aria-label={`Revoke ${key.name}`}
                      className="rounded-md p-1.5 text-slate-300 transition-colors hover:bg-red-50 hover:text-red-500"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Create API key">
        <form onSubmit={onCreate} className="space-y-4">
          <div>
            <Label htmlFor="key-name">Key name</Label>
            <Input id="key-name" placeholder="ci-pipeline" {...form.register("name")} />
            <FieldError message={form.formState.errors.name?.message} />
          </div>
          <fieldset className="space-y-2">
            <legend className="mb-1.5 text-xs font-medium text-slate-600">Scopes</legend>
            {["migrate", "read"].map((scope) => (
              <label key={scope} className="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
                <input type="checkbox" value={scope} {...form.register("scopes")} className="h-3.5 w-3.5 rounded border-slate-300 accent-slate-900" />
                <span className="font-mono text-xs">{scope}</span>
              </label>
            ))}
          </fieldset>
          <Button type="submit" loading={form.formState.isSubmitting}>Create key</Button>
        </form>
      </Modal>

      <Modal open={Boolean(createdKey)} onClose={() => setCreatedKey(null)} title="Your new API key">
        <p className="text-sm leading-relaxed text-slate-500">
          Copy this key now — it will not be shown again.
        </p>
        <div className="mt-4 flex items-center gap-2">
          <code className="code-input flex-1 truncate rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
            {createdKey}
          </code>
          <Button variant="secondary" size="sm" onClick={copyKey}>
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
