"use client";

import { useState } from "react";
import { useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Plus, X } from "lucide-react";
import { ruleDraftSchema, CHANGE_TYPES, type RuleDraftInput } from "@/schemas";
import { usePackBuilderStore, emptyRule, type RuleDraft } from "@/stores/pack-builder-store";
import { toast } from "@/stores/ui-store";
import { Button } from "@/components/ui/button";
import { Input, Select, Label, FieldError } from "@/components/ui/input";
import { Card, Badge } from "@/components/ui/card";

interface RulesStepProps {
  saving: boolean;
  publishAfterSave: boolean;
  onPublishChange: (value: boolean) => void;
  onBack: () => void;
  onSave: () => void;
}

export function RulesStep({ saving, publishAfterSave, onPublishChange, onBack, onSave }: RulesStepProps) {
  const versions = usePackBuilderStore((s) => s.versions);
  const selectedIndex = usePackBuilderStore((s) => s.selectedVersionIndex);
  const addRule = usePackBuilderStore((s) => s.addRule);
  const updateRule = usePackBuilderStore((s) => s.updateRule);
  const removeRule = usePackBuilderStore((s) => s.removeRule);

  const [editing, setEditing] = useState<null | { isNew: boolean; index: number }>(null);
  const ruleForm = useForm<RuleDraftInput>({
    resolver: zodResolver(ruleDraftSchema) as unknown as Resolver<RuleDraftInput>,
    defaultValues: emptyRule() as unknown as RuleDraftInput,
  });

  const current = versions[selectedIndex];
  if (!current) return null;

  const openEditor = (index: number | null) => {
    if (index === null) {
      setEditing({ isNew: true, index: -1 });
      ruleForm.reset(emptyRule() as unknown as RuleDraftInput);
    } else {
      setEditing({ isNew: false, index });
      ruleForm.reset(current.rules[index] as unknown as RuleDraftInput);
    }
  };

  const submitRule = ruleForm.handleSubmit((data) => {
    if (!editing) return;
    if (editing.isNew) {
      addRule(selectedIndex, data as unknown as RuleDraft);
      toast.success("Rule added");
    } else {
      updateRule(selectedIndex, editing.index, data as unknown as Partial<RuleDraft>);
      toast.success("Rule updated");
    }
    setEditing(null);
  });

  return (
    <div className="space-y-5">
      <Card className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/50 px-5 py-3">
          <h3 className="font-mono text-sm font-bold text-slate-900">v{current.version} · rules</h3>
          <Button variant="secondary" size="sm" type="button" onClick={() => openEditor(null)}>
            <Plus className="h-3.5 w-3.5" /> Add rule
          </Button>
        </div>
        <div className="divide-y divide-slate-50">
          {current.rules.map((rule, index) => (
            <div key={index} className="flex items-start justify-between gap-3 px-5 py-3.5 hover:bg-slate-50/50">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded bg-sky-50 px-1.5 py-0.5 font-mono text-[10px] text-sky-600">{rule.change_type}</span>
                  {rule.old_name && rule.new_name && (
                    <span className="font-mono text-xs text-slate-600">
                      {rule.old_name} → {rule.new_name}
                    </span>
                  )}
                  {rule.function_name && <span className="font-mono text-xs text-slate-500">fn: {rule.function_name}</span>}
                  {rule.argument_name && <span className="font-mono text-xs text-slate-500">arg: {rule.argument_name}</span>}
                </div>
                <p className="mt-1 truncate text-xs text-slate-500">{rule.description || "No description"}</p>
              </div>
              <Badge tone={rule.safety === "safe" ? "success" : rule.safety === "risky" ? "danger" : "warning"}>
                {rule.safety}
              </Badge>
              <div className="flex shrink-0 items-center gap-1">
                <Button variant="ghost" size="sm" type="button" onClick={() => openEditor(index)}>
                  Edit
                </Button>
                <button
                  type="button"
                  aria-label="Delete rule"
                  onClick={() => {
                    removeRule(selectedIndex, index);
                    toast.info("Rule removed");
                  }}
                  className="rounded-md p-1.5 text-slate-300 transition-colors hover:bg-red-50 hover:text-red-500"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
          {current.rules.length === 0 && (
            <p className="py-10 text-center text-xs text-slate-300">No rules yet — add your first rule.</p>
          )}
        </div>
      </Card>

      {editing && (
        <Card className="p-6">
          <h3 className="mb-4 text-sm font-semibold text-slate-900">{editing.isNew ? "New rule" : "Edit rule"}</h3>
          <form onSubmit={submitRule} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <Label>Change type</Label>
              <Select {...ruleForm.register("change_type")}>
                {CHANGE_TYPES.map((ct) => (
                  <option key={ct} value={ct}>
                    {ct}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label>Safety</Label>
              <Select {...ruleForm.register("safety")}>
                <option value="safe">safe</option>
                <option value="review_required">review_required</option>
                <option value="risky">risky</option>
              </Select>
            </div>
            <div className="sm:col-span-2">
              <Label>Description</Label>
              <Input placeholder="Rename Session.get to Client.get…" {...ruleForm.register("description")} />
              <FieldError message={ruleForm.formState.errors.description?.message} />
            </div>
            <div>
              <Label>Old name</Label>
              <Input className="font-mono" placeholder="Session" {...ruleForm.register("old_name")} />
            </div>
            <div>
              <Label>New name</Label>
              <Input className="font-mono" placeholder="Client" {...ruleForm.register("new_name")} />
            </div>
            <div>
              <Label>Function name</Label>
              <Input className="font-mono" placeholder="get" {...ruleForm.register("function_name")} />
            </div>
            <div>
              <Label>Argument name</Label>
              <Input className="font-mono" placeholder="timeout" {...ruleForm.register("argument_name")} />
            </div>
            <div className="sm:col-span-2">
              <Label>Replacement snippet</Label>
              <Input className="font-mono" placeholder="httpx.Client()" {...ruleForm.register("replacement")} />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 sm:col-span-2">
              <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-600">
                <input
                  type="checkbox"
                  checked={publishAfterSave}
                  onChange={(e) => onPublishChange(e.target.checked)}
                  className="h-3.5 w-3.5 rounded border-slate-300 accent-slate-900"
                />
                Publish immediately after saving
              </label>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" type="button" onClick={onBack}>
                  <ArrowLeft className="h-3 w-3" /> Back
                </Button>
                <Button variant="secondary" size="sm" type="button" disabled={saving} onClick={onSave}>
                  Save pack
                </Button>
                <Button size="sm" type="submit">
                  {editing.isNew ? "Add rule" : "Update rule"}
                </Button>
              </div>
            </div>
          </form>
        </Card>
      )}

      {!editing && (
        <div className="flex justify-between">
          <Button variant="secondary" size="sm" type="button" onClick={onBack}>
            <ArrowLeft className="h-3 w-3" /> Back
          </Button>
          <Button size="sm" type="button" loading={saving} onClick={onSave}>
            Save pack
          </Button>
        </div>
      )}
    </div>
  );
}
