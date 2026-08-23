"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Copy, Download, FileJson, ArrowRight, Terminal, FolderOpen } from "lucide-react";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { client } from "@/lib/api-client";
import { toast } from "@/stores/ui-store";

interface UpdatePackModalProps {
  open: boolean;
  onClose: () => void;
  packId: string;
  packName: string;
  libraryName: string;
}

function Step({
  number,
  icon: Icon,
  title,
  children,
  isLast,
}: {
  number: number;
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
  isLast?: boolean;
}) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 border-slate-200 bg-white font-mono text-xs font-bold text-slate-600">
          {number}
        </div>
        {!isLast && <div className="step-connector" />}
      </div>
      <div className="pb-6">
        <div className="flex items-center gap-2">
          <Icon className="h-3.5 w-3.5 text-slate-400" />
          <h4 className="text-sm font-semibold text-slate-900">{title}</h4>
        </div>
        <div className="mt-1 text-xs leading-relaxed text-slate-500">{children}</div>
      </div>
    </div>
  );
}

export function UpdatePackModal({ open, onClose, packId, packName, libraryName }: UpdatePackModalProps) {
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    client.current.packs
      .getPackContent(packId)
      .then((data) => setContent(JSON.stringify(data, null, 2)))
      .catch(() => toast.error("Failed to load pack content"))
      .finally(() => setLoading(false));
  }, [open, packId]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      toast.success("Copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy");
    }
  }, [content]);

  const handleDownload = useCallback(() => {
    const blob = new Blob([content], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "migration-pack.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast.success("File downloaded");
  }, [content]);

  return (
    <Modal open={open} onClose={onClose} title={`Update ${packName}`} className="max-w-2xl">
      {/* Steps */}
      <div className="mb-6">
        <Step number={1} icon={Download} title="Get the rules file">
          Copy or download the <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px] text-slate-600">migration-pack.json</code> below.
        </Step>
        <Step number={2} icon={FolderOpen} title="Replace in your project">
          Replace your existing <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px] text-slate-600">migration-pack.json</code> with this updated version.
        </Step>
        <Step number={3} icon={Terminal} title="Reinstall & verify" isLast>
          Run <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px] text-slate-600">pip install -e .</code> then verify with <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px] text-slate-600">migrate --help</code>.
        </Step>
      </div>

      {/* Code Viewer */}
      <div className="group relative overflow-hidden rounded-xl border border-slate-200 bg-slate-950">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-2">
          <div className="flex items-center gap-2">
            <FileJson className="h-3.5 w-3.5 text-emerald-400" />
            <span className="font-mono text-xs text-slate-400">migration-pack.json</span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
              {copied ? "Copied" : "Copy"}
            </button>
            <button
              onClick={handleDownload}
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <Download className="h-3 w-3" />
              Download
            </button>
          </div>
        </div>

        {/* Code Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-600 border-t-slate-300" />
          </div>
        ) : (
          <div className="max-h-[320px] overflow-auto">
            <pre className="p-4 text-xs leading-5 text-slate-300">
              <code>{highlightJson(content)}</code>
            </pre>
          </div>
        )}
      </div>

      {/* Footer hint */}
      <p className="mt-4 text-center text-[11px] text-slate-400">
        This updates only the rules. For a full package with engine files, use{" "}
        <button onClick={onClose} className="font-medium text-slate-600 underline underline-offset-2">
          Export
        </button>
        .
      </p>
    </Modal>
  );
}

function highlightJson(json: string): React.ReactNode {
  if (!json) return null;

  const lines = json.split("\n");
  return lines.map((line, i) => {
    const highlighted = line
      .replace(/"([^"]+)":/g, '<k>"$1"</k>:')
      .replace(/: "([^"]*)"/g, ': <s>"$1"</s>')
      .replace(/: (\d+)/g, ": <n>$1</n>")
      .replace(/: (true|false|null)/g, ": <b>$1</b>");

    return (
      <div key={i} className="flex">
        <span className="mr-4 inline-block w-6 select-none text-right text-slate-600">{i + 1}</span>
        <span
          dangerouslySetInnerHTML={{ __html: highlighted }}
          className="[&_k]:text-sky-300 [&_s]:text-emerald-300 [&_n]:text-amber-300 [&_b]:text-purple-300"
        />
      </div>
    );
  });
}
