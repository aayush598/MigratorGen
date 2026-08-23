import { create } from "zustand";

export type ToastKind = "success" | "error" | "info";

export interface Toast {
  id: string;
  kind: ToastKind;
  message: string;
}

interface UiState {
  sidebarOpen: boolean;
  toasts: Toast[];
  toggleSidebar: () => void;
  setSidebar: (open: boolean) => void;
  pushToast: (kind: ToastKind, message: string) => void;
  dismissToast: (id: string) => void;
}

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  toasts: [],
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebar: (open) => set({ sidebarOpen: open }),
  pushToast: (kind, message) =>
    set((s) => {
      const id = `t_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
      return { toasts: [...s.toasts.slice(-3), { id, kind, message }] };
    }),
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

export const toast = {
  success: (message: string) => useUiStore.getState().pushToast("success", message),
  error: (message: string) => useUiStore.getState().pushToast("error", message),
  info: (message: string) => useUiStore.getState().pushToast("info", message),
};
