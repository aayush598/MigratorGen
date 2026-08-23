"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight } from "lucide-react";
import { packDetailsSchema, type PackDetailsInput } from "@/schemas";
import { usePackBuilderStore } from "@/stores/pack-builder-store";
import { Button } from "@/components/ui/button";
import { Input, Textarea, Label, FieldError } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

export function DetailsStep({ onNext, isEditing = false }: { onNext: () => void; isEditing?: boolean }) {
  const form = useForm<PackDetailsInput>({
    resolver: zodResolver(packDetailsSchema),
    defaultValues: {
      name: usePackBuilderStore.getState().name || "",
      description: usePackBuilderStore.getState().description || "",
      library: usePackBuilderStore.getState().library || "",
    },
  });

  const onSubmit = (data: PackDetailsInput) => {
    usePackBuilderStore.getState().setDetails({
      name: data.name,
      description: data.description ?? "",
      library: data.library,
    });
    onNext();
  };

  return (
    <Card className="max-w-xl p-6">
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="pack-name">Display name</Label>
          <Input id="pack-name" placeholder="Requests to HTTPX" {...form.register("name")} />
          <FieldError message={form.formState.errors.name?.message} />
        </div>
        <div>
          <Label htmlFor="pack-library">Library slug</Label>
          <Input
            id="pack-library"
            placeholder="requests-to-httpx"
            className="font-mono"
            disabled={isEditing}
            {...form.register("library")}
          />
          {isEditing && <p className="mt-1 text-[11px] text-slate-400">Library slug cannot be changed while editing.</p>}
          <FieldError message={form.formState.errors.library?.message} />
        </div>
        <div>
          <Label htmlFor="pack-description">Description</Label>
          <Textarea id="pack-description" rows={3} placeholder="What does this migration cover?" {...form.register("description")} />
          <FieldError message={form.formState.errors.description?.message} />
        </div>
        <Button type="submit">
          Next: Versions <ArrowRight className="h-3.5 w-3.5" />
        </Button>
      </form>
    </Card>
  );
}
