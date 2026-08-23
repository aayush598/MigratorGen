"use client";

import { useEffect } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { useUiStore } from "@/stores/ui-store";
import { cn } from "@/lib/utils";

const icons = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
};

const toneStyles = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  error: "border-red-200 bg-red-50 text-red-800",
  info: "border-sky-200 bg-sky-50 text-sky-800",
};

export function Toaster() {
  const toasts = useUiStore((s) => s.toasts);
  const dismissToast = useUiStore((s) => s.dismissToast);
  useAutoDismiss();

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-80 flex-col gap-2">
      {toasts.map((t) => {
        const Icon = icons[t.kind];
        return (
          <div
            key={t.id}
            className={cn(
              "animate-scale-in pointer-events-auto flex items-start gap-2.5 rounded-xl border px-4 py-3 shadow-lg shadow-slate-900/5",
              toneStyles[t.kind],
            )}
          >
            <Icon className="mt-0.5 h-4 w-4 shrink-0" />
            <p className="min-w-0 flex-1 break-words text-sm">{t.message}</p>
            <button
              onClick={() => dismissToast(t.id)}
              className="shrink-0 opacity-50 transition-opacity hover:opacity-100"
              aria-label="Dismiss"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}

export function useAutoDismiss() {
  const toasts = useUiStore((s) => s.toasts);
  const dismissToast = useUiStore((s) => s.dismissToast);
  const ids = toasts.map((t) => t.id).join(",");

  useEffect(() => {
    if (!ids) return;
    const timers = ids.split(",").map((id) =>
      window.setTimeout(() => dismissToast(id), 4000),
    );
    return () => timers.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ids]);
}
