import { create } from "zustand";

export interface MigrationRun {
  id: string;
  library: string;
  sourceVersion: string;
  targetVersion: string;
  changeCount: number;
  wasModified: boolean;
  timestamp: number;
  sourceCode: string;
  transformedCode: string;
}

interface MigrationState {
  runs: MigrationRun[];
  lastRunAt: number | null;
  addRun: (run: Omit<MigrationRun, "id" | "timestamp">) => void;
  clearRuns: () => void;
}

const MAX_RUNS = 20;

function loadRuns(): MigrationRun[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem("mg_migration_runs") ?? "[]") as MigrationRun[];
  } catch {
    return [];
  }
}

function persist(runs: MigrationRun[], lastRunAt: number | null) {
  if (typeof window === "undefined") return;
  localStorage.setItem("mg_migration_runs", JSON.stringify(runs));
  localStorage.setItem("mg_last_run", lastRunAt ? String(lastRunAt) : "");
}

export const useMigrationStore = create<MigrationState>((set) => ({
  runs: [],
  lastRunAt: null,
  addRun: (run) =>
    set((state) => {
      const entry: MigrationRun = {
        ...run,
        id: `run_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
        timestamp: Date.now(),
      };
      const runs = [entry, ...state.runs].slice(0, MAX_RUNS);
      persist(runs, entry.timestamp);
      return { runs, lastRunAt: entry.timestamp };
    }),
  clearRuns: () =>
    set(() => {
      persist([], null);
      return { runs: [], lastRunAt: null };
    }),
}));

export function hydrateMigrationStore() {
  const runs = loadRuns();
  useMigrationStore.setState({ runs });
}
