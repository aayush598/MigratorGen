"use client";

import { useMemo } from "react";
import { computeSideBySide, computeWordDiff, type WordSegment } from "@/lib/line-diff";
import { cn } from "@/lib/utils";

function WordSpan({ segs, tone }: { segs: WordSegment[]; tone: "rose" | "emerald" }) {
  return (
    <>
      {segs.map((seg, i) =>
        seg.changed ? (
          <span
            key={i}
            className={cn(
              "rounded-[3px] px-0.5 font-semibold",
              tone === "rose" ? "bg-rose-200/70 text-rose-950" : "bg-emerald-200/70 text-emerald-950",
            )}
          >
            {seg.text}
          </span>
        ) : (
          <span key={i}>{seg.text}</span>
        ),
      )}
    </>
  );
}

export function SideBySideDiff({
  original,
  transformed,
}: {
  original: string;
  transformed: string;
}) {
  const rows = useMemo(() => computeSideBySide(original, transformed), [original, transformed]);
  const hasChanges = rows.some((r) => r.type !== "equal");

  if (!hasChanges) return null;

  const lineNumCell = (num: number | null, tint: string) => (
    <span className={cn("w-9 shrink-0 select-none bg-slate-50/50 px-1.5 text-right text-slate-300", num === null && "opacity-0")}>
      {num ?? ""}
    </span>
  );

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200">
      <div className="grid grid-cols-2 border-b border-slate-200 bg-slate-50 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
        <div className="border-r border-slate-200 px-3 py-2">Original</div>
        <div className="px-3 py-2">Migrated</div>
      </div>
      <div className="divide-y divide-slate-50 font-mono text-xs leading-relaxed">
        {rows.map((row, i) => {
          const wordSegs = row.type === "changed" ? computeWordDiff(row.left, row.right) : null;

          if (row.type === "equal") {
            return (
              <div key={i} className="grid grid-cols-2">
                <div className="flex border-r border-slate-100">
                  {lineNumCell(row.leftNum, "")}
                  <span className="whitespace-pre-wrap break-all px-2.5 py-1 text-slate-600">{row.left || "\u00A0"}</span>
                </div>
                <div className="flex">
                  {lineNumCell(row.rightNum, "")}
                  <span className="whitespace-pre-wrap break-all px-2.5 py-1 text-slate-600">{row.right || "\u00A0"}</span>
                </div>
              </div>
            );
          }

          if (row.type === "removed") {
            return (
              <div key={i} className="grid grid-cols-2">
                <div className="flex border-r border-slate-100 bg-rose-100/30">
                  <span className="w-9 shrink-0 select-none bg-rose-200/40 px-1.5 text-right text-rose-400">
                    {row.leftNum}
                  </span>
                  <span className="whitespace-pre-wrap break-all px-2.5 py-1 text-rose-800">
                    <span className="mr-1 select-none opacity-40">−</span>
                    {row.left}
                  </span>
                </div>
                <div />
              </div>
            );
          }

          if (row.type === "added") {
            return (
              <div key={i} className="grid grid-cols-2">
                <div className="border-r border-slate-100" />
                <div className="flex bg-emerald-100/30">
                  <span className="w-9 shrink-0 select-none bg-emerald-200/40 px-1.5 text-right text-emerald-500">
                    {row.rightNum}
                  </span>
                  <span className="whitespace-pre-wrap break-all px-2.5 py-1 text-emerald-900">
                    <span className="mr-1 select-none opacity-40">+</span>
                    {row.right}
                  </span>
                </div>
              </div>
            );
          }

          return (
            <div key={i} className="grid grid-cols-2">
              <div className="flex border-r border-slate-100 bg-rose-100/30">
                <span className="w-9 shrink-0 select-none bg-rose-200/40 px-1.5 text-right text-rose-400">
                  {row.leftNum}
                </span>
                <span className="whitespace-pre-wrap break-all px-2.5 py-1 text-rose-900/80">
                  <WordSpan segs={wordSegs!.leftSegs} tone="rose" />
                </span>
              </div>
              <div className="flex bg-emerald-100/30">
                <span className="w-9 shrink-0 select-none bg-emerald-200/40 px-1.5 text-right text-emerald-500">
                  {row.rightNum}
                </span>
                <span className="whitespace-pre-wrap break-all px-2.5 py-1 text-emerald-900/80">
                  <WordSpan segs={wordSegs!.rightSegs} tone="emerald" />
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
