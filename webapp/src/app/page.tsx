"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  Eye,
  Loader2,
  Play,
  RotateCcw,
  Terminal,
  Wand2,
  Zap,
} from "lucide-react";
import { useUser, useClerk } from "@clerk/nextjs";

type DiffKind = "context" | "changed";
type DiffLine = { kind: DiffKind; before: string; after: string };

const DIFF_ROWS: DiffLine[] = [
  { kind: "context", before: "# fetch_users.py", after: "# fetch_users.py" },
  { kind: "changed", before: "import requests", after: "import httpx" },
  { kind: "context", before: "", after: "" },
  { kind: "context", before: 'BASE_URL = "https://api.acme.dev"', after: 'BASE_URL = "https://api.acme.dev"' },
  { kind: "context", before: "def fetch_users():", after: "def fetch_users():" },
  { kind: "context", before: '    headers = {"accept": "application/json"}', after: '    headers = {"accept": "application/json"}' },
  { kind: "changed", before: "    session = requests.Session()", after: "    client = httpx.Client()" },
  { kind: "changed", before: "    resp = session.get(BASE_URL, headers=headers)", after: "    resp = client.get(BASE_URL, headers=headers)" },
  { kind: "context", before: "    resp.raise_for_status()", after: "    resp.raise_for_status()" },
  { kind: "context", before: '    return resp.json()["users"]', after: '    return resp.json()["users"]' },
  { kind: "context", before: "", after: "" },
  { kind: "context", before: "print(fetch_users())", after: "print(fetch_users())" },
];

const CHANGES_COUNT = DIFF_ROWS.filter((row) => row.kind === "changed").length;

const PY_TOKEN_RE =
  /(f?"[^"]*"|f?'[^']*')|\b(import|from|def|return|with|as|for|in|if|else)\b|\b(requests)\b|\b(httpx)\b/g;

function renderPyLine(line: string) {
  if (!line) return "\u00A0";
  const nodes: React.ReactNode[] = [];
  const regex = new RegExp(PY_TOKEN_RE.source, "g");
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(line)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(<span key={nodes.length}>{line.slice(lastIndex, match.index)}</span>);
    }
    if (match[1]) {
      nodes.push(
        <span key={nodes.length} className="text-emerald-600">
          {match[1]}
        </span>
      );
    } else if (match[2]) {
      nodes.push(
        <span key={nodes.length} className="text-slate-400">
          {match[2]}
        </span>
      );
    } else if (match[3]) {
      nodes.push(
        <span key={nodes.length} className="text-red-500">
          {match[3]}
        </span>
      );
    } else if (match[4]) {
      nodes.push(
        <span key={nodes.length} className="text-emerald-500">
          {match[4]}
        </span>
      );
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < line.length) {
    nodes.push(<span key={nodes.length}>{line.slice(lastIndex)}</span>);
  }
  return nodes;
}

function CountUp({ target, suffix }: { target: number; suffix: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [value, setValue] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let frame = 0;
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries[0].isIntersecting) return;
        observer.disconnect();
        const duration = 2000;
        const start = performance.now();
        const tick = (now: number) => {
          const progress = Math.min((now - start) / duration, 1);
          const eased = 1 - Math.pow(1 - progress, 3);
          setValue(Math.round(eased * target));
          if (progress < 1) frame = requestAnimationFrame(tick);
        };
        frame = requestAnimationFrame(tick);
      },
      { threshold: 0.4 }
    );
    observer.observe(el);
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [target]);

  return (
    <span ref={ref} className="tabular-nums">
      {value}
      {suffix}
    </span>
  );
}

const STATS = [
  { target: 250, suffix: "+", label: "Migration rules" },
  { target: 470, suffix: "", label: "Tests passing" },
  { target: 12, suffix: "", label: "Library packs" },
];

type Step = {
  number: string;
  title: string;
  description: string;
  mockupType: "parse" | "generate" | "apply";
};

const STEPS: Step[] = [
  {
    number: "01",
    title: "Parse",
    description:
      "Point MigratorGen at an upstream changelog. It extracts every breaking change into a structured, versioned manifest.",
    mockupType: "parse",
  },
  {
    number: "02",
    title: "Generate",
    description:
      "Each breaking change becomes a deterministic AST rule, reviewed and versioned, never a blind regex swap.",
    mockupType: "generate",
  },
  {
    number: "03",
    title: "Apply",
    description:
      "Rewrites land as a single transaction-safe commit. Type-check and tests must pass or nothing is merged.",
    mockupType: "apply",
  },
];

const LIBRARIES = [
  {
    name: "requests-to-httpx",
    rules: 3,
    description: "Sessions, top-level verbs and timeout handling rewritten for the httpx API surface.",
    command: "migratorgen install requests-to-httpx",
    icon: Terminal,
  },
  {
    name: "pydantic-v1-to-v2",
    rules: 20,
    description: "Validators, Config classes and .dict() calls migrated to the v2 model API.",
    command: "migratorgen install pydantic-v1-to-v2",
    icon: Wand2,
  },
  {
    name: "fastapi-deps",
    rules: 4,
    description: "Depends() signatures, background tasks and lifespan handlers brought up to date.",
    command: "migratorgen install fastapi-deps",
    icon: Zap,
  },
  {
    name: "cocotb-v2",
    rules: 1,
    description: "Testbench coroutines and scheduler calls ported to cocotb 2.x semantics.",
    command: "migratorgen install cocotb-v2",
    icon: Play,
  },
];

type Plan = {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  cta: string;
  highlighted: boolean;
};

const PLANS: Plan[] = [
  {
    name: "Free",
    price: "$0",
    period: "",
    description: "For solo developers exploring automated migrations.",
    features: ["1 library pack", "10 migrations per month", "CLI access", "Community support"],
    cta: "Start free",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$29",
    period: "/mo",
    description: "For teams shipping against fast-moving dependencies.",
    features: ["All 12 library packs", "Unlimited migrations", "Custom YAML rules", "CI integration", "Priority support"],
    cta: "Get Pro",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For organizations with private forks and compliance needs.",
    features: ["Private library packs", "On-prem runners", "SSO and audit logs", "Dedicated support"],
    cta: "Contact sales",
    highlighted: false,
  },
];

const MOCKUP_CARD_CLASS =
  "visual-mockup relative h-[140px] overflow-hidden rounded-xl border border-slate-200 bg-white p-4";

function ParseMockup() {
  return (
    <div className={MOCKUP_CARD_CLASS}>
      <div className="relative h-full w-full">
        <svg viewBox="0 0 280 100" className="h-full w-full" aria-hidden="true">
          <rect x="20" y="10" width="80" height="80" rx="6" fill="#f8fafc" stroke="#e2e8f0" strokeWidth="1.5" />
          <line x1="32" y1="28" x2="88" y2="28" stroke="#cbd5e1" strokeWidth="2" strokeLinecap="round" />
          <line x1="32" y1="40" x2="75" y2="40" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
          <line x1="32" y1="52" x2="82" y2="52" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
          <line x1="32" y1="64" x2="60" y2="64" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
          <line x1="32" y1="76" x2="70" y2="76" stroke="#e2e8f0" strokeWidth="2" strokeLinecap="round" />
          <g style={{ animation: "mockSlideRight 4s ease-in-out infinite" }}>
            <circle cx="60" cy="50" r="22" fill="none" stroke="#0f172a" strokeWidth="2" opacity="0.8" />
            <line x1="76" y1="66" x2="90" y2="80" stroke="#0f172a" strokeWidth="2.5" strokeLinecap="round" opacity="0.8" />
            <circle cx="60" cy="50" r="14" fill="none" stroke="#0f172a" strokeWidth="0.5" opacity="0.2" />
          </g>
          <g style={{ animation: "mockFloat 3s ease-in-out infinite" }}>
            <rect x="130" y="12" width="60" height="22" rx="4" fill="#eff6ff" stroke="#bfdbfe" strokeWidth="1" />
            <text x="160" y="27" textAnchor="middle" fontSize="9" fill="#3b82f6" fontFamily="JetBrains Mono, monospace" fontWeight="500">breaking</text>
          </g>
          <g style={{ animation: "mockFloat 3.5s ease-in-out 0.5s infinite" }}>
            <rect x="200" y="18" width="52" height="20" rx="4" fill="#f0fdf4" stroke="#bbf7d0" strokeWidth="1" />
            <text x="226" y="32" textAnchor="middle" fontSize="9" fill="#22c55e" fontFamily="JetBrains Mono, monospace" fontWeight="500">v3.0</text>
          </g>
          <g style={{ animation: "mockFloat 4s ease-in-out 1s infinite" }}>
            <rect x="140" y="48" width="68" height="20" rx="4" fill="#fefce8" stroke="#fde68a" strokeWidth="1" />
            <text x="174" y="62" textAnchor="middle" fontSize="9" fill="#ca8a04" fontFamily="JetBrains Mono, monospace" fontWeight="500">deprecated</text>
          </g>
          <g style={{ animation: "mockPulse 3s ease-in-out infinite" }}>
            <rect x="210" y="55" width="56" height="20" rx="4" fill="#fdf2f8" stroke="#fbcfe8" strokeWidth="1" />
            <text x="238" y="69" textAnchor="middle" fontSize="9" fill="#db2777" fontFamily="JetBrains Mono, monospace" fontWeight="500">removed</text>
          </g>
        </svg>
      </div>
    </div>
  );
}

function GenerateMockup() {
  return (
    <div className={MOCKUP_CARD_CLASS}>
      <div className="relative h-full w-full">
        <svg viewBox="0 0 280 100" className="h-full w-full" aria-hidden="true">
          <g style={{ animation: "mockFloat 3s ease-in-out infinite" }}>
            <rect x="10" y="15" width="50" height="30" rx="4" fill="#f1f5f9" stroke="#cbd5e1" strokeWidth="1" />
            <text x="35" y="34" textAnchor="middle" fontSize="8" fill="#475569" fontFamily="JetBrains Mono, monospace">Session</text>
          </g>
          <g style={{ animation: "mockFloat 3.2s ease-in-out 0.3s infinite" }}>
            <rect x="10" y="55" width="50" height="30" rx="4" fill="#f1f5f9" stroke="#cbd5e1" strokeWidth="1" />
            <text x="35" y="74" textAnchor="middle" fontSize="8" fill="#475569" fontFamily="JetBrains Mono, monospace">.get()</text>
          </g>
          <g style={{ animation: "mockFloat 3.4s ease-in-out 0.6s infinite" }}>
            <rect x="10" y="35" width="50" height="30" rx="4" fill="#fef2f2" stroke="#fecaca" strokeWidth="1" />
            <text x="35" y="54" textAnchor="middle" fontSize="8" fill="#ef4444" fontFamily="JetBrains Mono, monospace">timeout</text>
          </g>
          <g style={{ transformOrigin: "140px 50px", animation: "orbitSlow 6s linear infinite" }}>
            <circle cx="140" cy="50" r="16" fill="#f8fafc" stroke="#0f172a" strokeWidth="1.5" />
            <path d="M 134 44 L 146 44 L 146 56 L 134 56 Z" fill="none" stroke="#0f172a" strokeWidth="1" />
            <circle cx="140" cy="50" r="3" fill="#0f172a" />
          </g>
          <path d="M 80 50 L 110 50" stroke="#94a3b8" strokeWidth="1.5" strokeDasharray="4 3" markerEnd="url(#arrowRight)" />
          <path d="M 170 50 L 200 50" stroke="#94a3b8" strokeWidth="1.5" strokeDasharray="4 3" markerEnd="url(#arrowRight)" />
          <defs>
            <marker id="arrowRight" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
              <path d="M 0 0 L 8 3 L 0 6 Z" fill="#94a3b8" />
            </marker>
          </defs>
          <g style={{ animation: "mockFloat 3s ease-in-out 0.2s infinite" }}>
            <rect x="210" y="15" width="60" height="30" rx="4" fill="#f0fdf4" stroke="#bbf7d0" strokeWidth="1" />
            <text x="240" y="34" textAnchor="middle" fontSize="8" fill="#22c55e" fontFamily="JetBrains Mono, monospace">Client</text>
          </g>
          <g style={{ animation: "mockFloat 3.2s ease-in-out 0.5s infinite" }}>
            <rect x="210" y="55" width="60" height="30" rx="4" fill="#f0fdf4" stroke="#bbf7d0" strokeWidth="1" />
            <text x="240" y="74" textAnchor="middle" fontSize="8" fill="#22c55e" fontFamily="JetBrains Mono, monospace">.get()</text>
          </g>
          <g style={{ animation: "mockFloat 3.4s ease-in-out 0.8s infinite" }}>
            <rect x="210" y="35" width="60" height="30" rx="4" fill="#ecfdf5" stroke="#a7f3d0" strokeWidth="1" />
            <text x="240" y="54" textAnchor="middle" fontSize="8" fill="#10b981" fontFamily="JetBrains Mono, monospace">timeout=</text>
          </g>
        </svg>
      </div>
    </div>
  );
}

function ApplyMockup() {
  const files = [
    { name: "fetch_users.py", delay: 0 },
    { name: "models/user.py", delay: 0.3 },
    { name: "api/client.py", delay: 0.6 },
    { name: "tests/test_api.py", delay: 0.9 },
  ];
  return (
    <div className={MOCKUP_CARD_CLASS}>
      <div className="relative h-full w-full">
        <svg viewBox="0 0 280 100" className="h-full w-full" aria-hidden="true">
          {files.map((file, i) => {
            const row = Math.floor(i / 2);
            const col = i % 2;
            const x = 20 + col * 130;
            const y = 10 + row * 42;
            return (
              <g key={file.name} style={{ animation: `mockFloat 3s ease-in-out ${i * 0.4}s infinite` }}>
                <rect x={x} y={y} width="110" height="32" rx="5" fill="#f8fafc" stroke="#e2e8f0" strokeWidth="1" />
                <rect x={x} y={y} width="16" height="8" rx="2" fill="#e2e8f0" />
                <line x1={x + 8} y1={y} x2={x + 8} y2={y + 8} stroke="#f8fafc" strokeWidth="1" />
                <rect x={x + 5} y={y + 10} width={12} height={14} rx="1.5" fill="#e2e8f0" stroke="#cbd5e1" strokeWidth="0.5" />
                <line x1={x + 8} y1={y + 14} x2={x + 14} y2={y + 14} stroke="#94a3b8" strokeWidth="1" />
                <line x1={x + 8} y1={y + 17} x2={x + 13} y2={y + 17} stroke="#94a3b8" strokeWidth="1" />
                <line x1={x + 8} y1={y + 20} x2={x + 15} y2={y + 20} stroke="#94a3b8" strokeWidth="1" />
                <text x={x + 26} y={y + 21} fontSize="8" fill="#475569" fontFamily="JetBrains Mono, monospace">{file.name}</text>
                <g style={{ animation: `mockGrowCheck 2s ease-out ${file.delay + 0.5}s infinite both` }}>
                  <circle cx={x + 96} cy={y + 16} r="8" fill="#dcfce7" />
                  <path d={`M ${x + 92} ${y + 16} L ${x + 95} ${y + 19} L ${x + 101} ${y + 13}`} fill="none" stroke="#16a34a" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </g>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

function StepMockup({ type }: { type: Step["mockupType"] }) {
  if (type === "parse") return <ParseMockup />;
  if (type === "generate") return <GenerateMockup />;
  return <ApplyMockup />;
}

const VEHICLE_PATH = "M 30,95 C 90,95 120,15 200,15 S 280,95 360,95 S 440,15 520,15 S 600,95 680,95 S 760,15 840,15 S 920,95 1000,95 S 1080,15 1160,15";

const VERSION_NODES = [
  { x: 30, y: 95, label: "v1.0", major: true },
  { x: 200, y: 15, label: "v1.1", major: false },
  { x: 360, y: 95, label: "v1.2", major: false },
  { x: 520, y: 15, label: "v1.3", major: false },
  { x: 680, y: 95, label: "v1.5", major: false },
  { x: 840, y: 15, label: "v1.8", major: false },
  { x: 1160, y: 15, label: "v2.0", major: true },
];

export default function Home() {
  const { user } = useUser();
  const { signOut } = useClerk();
  const [diffVisible, setDiffVisible] = useState<number[]>([]);
  const [previewActive, setPreviewActive] = useState(false);
  const [applyState, setApplyState] = useState<"idle" | "applying" | "applied">("idle");
  const [runId, setRunId] = useState(0);
  const [activeStep, setActiveStep] = useState(0);
  const timersRef = useRef<number[]>([]);

  useEffect(() => {
    setDiffVisible([]);
    const ids: number[] = [];
    DIFF_ROWS.forEach((_, index) => {
      ids.push(
        window.setTimeout(() => {
          setDiffVisible((previous) => [...previous, index]);
        }, 400 + index * 150)
      );
    });
    return () => ids.forEach(clearTimeout);
  }, [runId]);

  useEffect(() => {
    const timers = timersRef.current;
    return () => timers.forEach(clearTimeout);
  }, []);

  const handlePreview = () => {
    setPreviewActive(true);
    timersRef.current.push(window.setTimeout(() => setPreviewActive(false), 1500));
  };

  const handleApply = () => {
    if (applyState !== "idle") return;
    setApplyState("applying");
    timersRef.current.push(window.setTimeout(() => setApplyState("applied"), 2000));
  };

  const handleReset = () => {
    setApplyState("idle");
    setPreviewActive(false);
    setRunId((previous) => previous + 1);
  };

  return (
    <div className="min-h-screen bg-[#fafafa] text-slate-900">
      <header className="sticky top-0 z-50 border-b border-slate-200/70 bg-white/70 backdrop-blur-md">
        <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <a href="#" className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900">
              <Zap className="h-4 w-4 text-white" fill="currentColor" />
            </span>
            <span className="font-semibold tracking-tight">MigratorGen</span>
          </a>
          <div className="hidden items-center gap-8 text-sm font-medium text-slate-500 md:flex">
            <a href="#product" className="transition-colors hover:text-slate-900">Product</a>
            <a href="#libraries" className="transition-colors hover:text-slate-900">Libraries</a>
            <a href="#pricing" className="transition-colors hover:text-slate-900">Pricing</a>
          </div>
          <div className="flex items-center gap-4">
            {user ? (
              <>
                <a href="/dashboard" className="text-sm font-medium text-slate-600 transition-colors hover:text-slate-900">
                  Dashboard
                </a>
                <button
                  onClick={() => { signOut(); window.location.reload(); }}
                  className="text-sm font-medium text-slate-500 transition-colors hover:text-slate-700"
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <a href="/auth/login" className="text-sm font-medium text-slate-600 transition-colors hover:text-slate-900">
                  Sign in
                </a>
                <a
                  href="/auth/register"
                  className="btn-press inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-800"
                >
                  Get started
                  <ArrowRight className="h-3.5 w-3.5" />
                </a>
              </>
            )}
          </div>
        </nav>
      </header>

      <main>
        <section id="product" className="hero-bg pb-24 pt-20 md:pt-28">
          <div aria-hidden className="pointer-events-none absolute inset-0 hero-grid" />
          <div aria-hidden className="pointer-events-none absolute inset-0">
            <div className="animate-float-1 absolute left-[8%] top-[15%] h-72 w-72 rounded-full bg-slate-200/40 blur-3xl" />
            <div className="animate-float-2 absolute right-[10%] top-[30%] h-80 w-80 rounded-full bg-slate-200/40 blur-3xl" />
            <div className="animate-float-3 absolute left-[35%] top-[55%] h-96 w-96 rounded-full bg-slate-200/40 blur-3xl" />
            <svg viewBox="0 0 1200 800" preserveAspectRatio="xMidYMid slice" className="absolute inset-0 h-full w-full">
              <g className="animate-drift-left" style={{ animationDuration: "16s" }}>
                <circle cx="100" cy="120" r="45" fill="none" stroke="#e2e8f0" strokeWidth="0.8" opacity="0.25" />
              </g>
              <g className="animate-drift-right" style={{ animationDuration: "14s" }}>
                <circle cx="1100" cy="600" r="40" fill="none" stroke="#e2e8f0" strokeWidth="0.8" opacity="0.2" />
              </g>
              <g className="animate-spin-slow" style={{ animationDuration: "50s" }}>
                <polygon points="150,650 180,670 180,710 150,730 120,710 120,670" fill="none" stroke="#e2e8f0" strokeWidth="0.6" opacity="0.2" />
              </g>
              <g className="animate-spin-reverse" style={{ animationDuration: "60s" }}>
                <polygon points="1050,150 1075,168 1075,204 1050,222 1025,204 1025,168" fill="none" stroke="#e2e8f0" strokeWidth="0.5" opacity="0.18" />
              </g>
              <g className="animate-pulse-ring" style={{ animationDuration: "8s" }}>
                <circle cx="300" cy="400" r="80" fill="none" stroke="#e2e8f0" strokeWidth="0.4" opacity="0.15" />
              </g>
              <g className="animate-cross-spin" style={{ animationDuration: "12s" }}>
                <line x1="900" y1="300" x2="930" y2="330" stroke="#d1d5db" strokeWidth="0.8" opacity="0.15" />
                <line x1="930" y1="300" x2="900" y2="330" stroke="#d1d5db" strokeWidth="0.8" opacity="0.15" />
              </g>
              {[200, 500, 750, 1000].map((x, i) => (
                <g key={x} className="animate-wave-y" style={{ animationDuration: `${5 + i}s`, animationDelay: `${i * 0.5}s` }}>
                  <circle cx={x} cy={200 + (i % 3) * 150} r={2 + (i % 2)} fill="#d1d5db" opacity="0.15" />
                </g>
              ))}
            </svg>
          </div>

          <div className="relative mx-auto max-w-3xl px-6 text-center">
            <span className="animate-fade-up stagger-1 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3.5 py-1.5 text-xs font-medium text-slate-600 shadow-sm">
              Introducing MigratorGen v1.0
              <ArrowRight className="h-3 w-3 text-slate-400" />
            </span>
            <h1 className="animate-fade-up stagger-2 mt-6 text-5xl font-extrabold leading-[1.05] tracking-tight md:text-6xl lg:text-7xl">
              Migrate Python code
              <br />
              <span className="gradient-text">with confidence</span>
            </h1>
            <p className="animate-fade-up stagger-3 mx-auto mt-6 max-w-xl text-lg leading-relaxed text-slate-500">
              AST-accurate transformations driven by upstream changelogs. Every rewrite is deterministic,
              reviewable and safe to merge, across entire repositories.
            </p>
            <div className="animate-fade-up stagger-4 mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <a
                href={user ? "/dashboard" : "/auth/register"}
                className="btn-press inline-flex items-center gap-2 rounded-xl bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-slate-800"
              >
                Start migrating
                <ArrowRight className="h-4 w-4" />
              </a>
              <a
                href="#how"
                className="btn-press inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-700 transition-colors hover:border-slate-300"
              >
                <Play className="h-4 w-4 text-slate-400" fill="currentColor" />
                See how it works
              </a>
            </div>
          </div>

          <div className="animate-fade-up stagger-6 relative mx-auto mt-16 max-w-4xl px-6">
            <div className="diff-container overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-900/5">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
                    <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
                    <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
                  </div>
                  <span className="font-mono text-xs text-slate-500">requests-to-httpx</span>
                </div>
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 font-mono text-[10px] text-slate-500">
                  v2.31.1 → v0.27.0
                </span>
              </div>

              <div className="grid md:grid-cols-2">
                <div className="border-b border-slate-100 md:border-b-0 md:border-r">
                  <div className="border-b border-slate-100 px-4 py-2 text-[10px] font-semibold tracking-widest text-slate-400">
                    BEFORE
                  </div>
                  <div className="min-h-[264px] overflow-x-auto py-2 font-mono text-[11px] leading-5 text-slate-800 md:text-xs">
                    {DIFF_ROWS.map((row, index) =>
                      diffVisible.includes(index) ? (
                        <div
                          key={index}
                          className={`animate-fade-up whitespace-pre px-4 ${
                            row.kind === "changed"
                              ? `border-l-2 border-red-400 bg-red-50 ${previewActive ? "animate-pulse" : ""}`
                              : ""
                          }`}
                        >
                          {renderPyLine(row.before)}
                        </div>
                      ) : null
                    )}
                  </div>
                </div>

                <div>
                  <div className="border-b border-slate-100 px-4 py-2 text-[10px] font-semibold tracking-widest text-slate-400">
                    AFTER
                  </div>
                  <div className="min-h-[264px] overflow-x-auto py-2 font-mono text-[11px] leading-5 text-slate-800 md:text-xs">
                    {DIFF_ROWS.map((row, index) =>
                      diffVisible.includes(index) ? (
                        <div
                          key={index}
                          className={`animate-fade-up whitespace-pre px-4 ${
                            row.kind === "changed"
                              ? `border-l-2 border-emerald-400 bg-emerald-50 ${previewActive ? "animate-pulse" : ""}`
                              : ""
                          }`}
                        >
                          {renderPyLine(row.after)}
                        </div>
                      ) : null
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3">
                <span className="font-mono text-xs text-slate-500">
                  {CHANGES_COUNT} changes · 0 errors
                </span>
                <div className="flex items-center gap-2">
                  {applyState === "applied" ? (
                    <button
                      onClick={handleReset}
                      className="btn-press inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:border-slate-300"
                    >
                      <RotateCcw className="h-3.5 w-3.5" />
                      Reset
                    </button>
                  ) : (
                    <button
                      onClick={handlePreview}
                      className="btn-press inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:border-slate-300"
                    >
                      <Eye className="h-3.5 w-3.5 text-slate-400" />
                      Preview
                    </button>
                  )}
                  <button
                    onClick={handleApply}
                    disabled={applyState !== "idle"}
                    className={`btn-press inline-flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-xs font-medium text-white transition-colors ${
                      applyState === "applied"
                        ? "bg-emerald-600"
                        : applyState === "applying"
                          ? "cursor-wait bg-slate-400"
                          : "bg-slate-900 hover:bg-slate-800"
                    }`}
                  >
                    {applyState === "idle" && (
                      <>
                        Apply
                        <Wand2 className="h-3.5 w-3.5" />
                      </>
                    )}
                    {applyState === "applying" && (
                      <>
                        Applying
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      </>
                    )}
                    {applyState === "applied" && (
                      <>
                        Applied!
                        <Check className="h-3.5 w-3.5" />
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="relative overflow-hidden border-y border-slate-100 bg-white py-20">
          <div className="bg-svg-decor" aria-hidden="true">
            <svg viewBox="0 0 1200 300" preserveAspectRatio="xMidYMid slice">
              <defs>
                <pattern id="statsGrid" width="60" height="60" patternUnits="userSpaceOnUse">
                  <circle cx="30" cy="30" r="1" fill="#cbd5e1" opacity="0.3" />
                </pattern>
              </defs>
              <rect width="1200" height="300" fill="url(#statsGrid)" className="animate-grid-x" />
              <g className="animate-drift-left" style={{ animationDuration: "10s" }}>
                <circle cx="120" cy="60" r="30" fill="none" stroke="#e2e8f0" strokeWidth="1" opacity="0.5" />
                <circle cx="120" cy="60" r="50" fill="none" stroke="#e2e8f0" strokeWidth="0.5" opacity="0.3" />
              </g>
              <g className="animate-drift-right" style={{ animationDuration: "12s" }}>
                <rect x="950" y="80" width="40" height="40" rx="8" fill="none" stroke="#e2e8f0" strokeWidth="1" opacity="0.4" transform="rotate(15 970 100)" />
              </g>
              <g className="animate-pulse-ring" style={{ animationDuration: "5s" }}>
                <circle cx="600" cy="150" r="80" fill="none" stroke="#e2e8f0" strokeWidth="0.5" opacity="0.3" />
              </g>
              <g className="animate-fade-drift" style={{ animationDuration: "7s", animationDelay: "1s" }}>
                <line x1="300" y1="40" x2="340" y2="80" stroke="#d1d5db" strokeWidth="1" opacity="0.3" />
                <line x1="340" y1="40" x2="300" y2="80" stroke="#d1d5db" strokeWidth="1" opacity="0.3" />
              </g>
              <g className="animate-fade-drift" style={{ animationDuration: "6s", animationDelay: "2s" }}>
                <line x1="860" y1="180" x2="900" y2="220" stroke="#d1d5db" strokeWidth="1" opacity="0.3" />
                <line x1="900" y1="180" x2="860" y2="220" stroke="#d1d5db" strokeWidth="1" opacity="0.3" />
              </g>
              <g className="animate-wave-y" style={{ animationDuration: "4s" }}>
                <circle cx="200" cy="220" r="3" fill="#d1d5db" opacity="0.3" />
              </g>
              <g className="animate-wave-y" style={{ animationDuration: "5s", animationDelay: "0.5s" }}>
                <circle cx="500" cy="50" r="2.5" fill="#d1d5db" opacity="0.25" />
              </g>
              <g className="animate-wave-y" style={{ animationDuration: "4.5s", animationDelay: "1s" }}>
                <circle cx="780" cy="250" r="3" fill="#d1d5db" opacity="0.3" />
              </g>
              <g className="animate-wave-y" style={{ animationDuration: "6s", animationDelay: "1.5s" }}>
                <circle cx="1050" cy="130" r="2" fill="#d1d5db" opacity="0.2" />
              </g>
            </svg>
          </div>
          <div className="mx-auto grid max-w-4xl grid-cols-1 gap-10 px-6 text-center sm:grid-cols-3">
            {STATS.map((stat) => (
              <div key={stat.label}>
                <p className="text-4xl font-bold tracking-tight text-slate-900 md:text-5xl">
                  <CountUp target={stat.target} suffix={stat.suffix} />
                </p>
                <p className="mt-2 text-sm font-medium text-slate-500">{stat.label}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="how" className="relative overflow-hidden py-24">
          <div className="bg-svg-decor" aria-hidden="true">
            <svg viewBox="0 0 1200 600" preserveAspectRatio="xMidYMid slice">
              <defs>
                <pattern id="howGrid" width="80" height="80" patternUnits="userSpaceOnUse">
                  <path d="M 80 0 L 0 0 0 80" fill="none" stroke="#e5e7eb" strokeWidth="0.5" opacity="0.4" />
                </pattern>
              </defs>
              <rect width="1200" height="600" fill="url(#howGrid)" className="animate-grid-y" />
              <g className="animate-drift-left" style={{ animationDuration: "12s" }}>
                <circle cx="80" cy="100" r="40" fill="none" stroke="#d1d5db" strokeWidth="1" strokeDasharray="4 4" className="animate-line-dash" />
              </g>
              <g className="animate-drift-right" style={{ animationDuration: "14s" }}>
                <circle cx="1100" cy="400" r="35" fill="none" stroke="#d1d5db" strokeWidth="1" strokeDasharray="4 4" className="animate-line-dash" />
              </g>
              <g className="animate-cross-spin" style={{ animationDuration: "8s" }}>
                <line x1="180" y1="280" x2="210" y2="310" stroke="#d1d5db" strokeWidth="1" opacity="0.4" />
                <line x1="210" y1="280" x2="180" y2="310" stroke="#d1d5db" strokeWidth="1" opacity="0.4" />
              </g>
              <g className="animate-cross-spin" style={{ animationDuration: "9s", animationDelay: "2s" }}>
                <line x1="1000" y1="120" x2="1030" y2="150" stroke="#d1d5db" strokeWidth="1" opacity="0.4" />
                <line x1="1030" y1="120" x2="1000" y2="150" stroke="#d1d5db" strokeWidth="1" opacity="0.4" />
              </g>
              <g className="animate-pulse-ring" style={{ animationDuration: "6s" }}>
                <circle cx="300" cy="500" r="60" fill="none" stroke="#e2e8f0" strokeWidth="0.5" opacity="0.3" />
              </g>
              <g className="animate-pulse-ring" style={{ animationDuration: "7s", animationDelay: "1s" }}>
                <circle cx="900" cy="80" r="50" fill="none" stroke="#e2e8f0" strokeWidth="0.5" opacity="0.25" />
              </g>
              <g className="animate-hex-float" style={{ animationDuration: "9s" }}>
                <polygon points="500,30 530,50 530,90 500,110 470,90 470,50" fill="none" stroke="#e5e7eb" strokeWidth="0.8" opacity="0.35" />
              </g>
              <g className="animate-hex-float" style={{ animationDuration: "11s", animationDelay: "3s" }}>
                <polygon points="750,480 775,496 775,528 750,544 725,528 725,496" fill="none" stroke="#e5e7eb" strokeWidth="0.8" opacity="0.3" />
              </g>
              {[160, 380, 620, 860, 1060].map((x, i) => (
                <g key={x} className="animate-wave-y" style={{ animationDuration: `${4 + i * 0.7}s`, animationDelay: `${i * 0.4}s` }}>
                  <circle cx={x} cy={200 + (i % 3) * 100} r="2" fill="#d1d5db" opacity="0.3" />
                </g>
              ))}
              <g className="animate-fade-drift" style={{ animationDuration: "8s" }}>
                <rect x="50" y="400" width="24" height="24" rx="4" fill="none" stroke="#e2e8f0" strokeWidth="0.8" opacity="0.3" transform="rotate(30 62 412)" />
              </g>
              <g className="animate-fade-drift" style={{ animationDuration: "9s", animationDelay: "2s" }}>
                <rect x="1080" y="200" width="20" height="20" rx="4" fill="none" stroke="#e2e8f0" strokeWidth="0.8" opacity="0.3" transform="rotate(-20 1090 210)" />
              </g>
            </svg>
          </div>
          <div className="mx-auto max-w-6xl px-6">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Three steps to clean code.</h2>
              <p className="mt-3 text-lg text-slate-500">From changelog to commit in under a minute.</p>
            </div>

            <div className="mx-auto mt-14 flex max-w-4xl flex-col items-center">
              {STEPS.map((step, index) => (
                <Fragment key={step.number}>
                  {index > 0 && <div className="step-connector" />}
                  <button
                    onClick={() => setActiveStep(index)}
                    className={`step-card ${activeStep === index ? "active" : ""} grid w-full grid-cols-1 gap-6 rounded-2xl border border-slate-200 bg-white p-6 text-left sm:grid-cols-[auto_1fr] md:grid-cols-[auto_1fr_320px] md:items-center md:p-8`}
                  >
                    <span
                      className={`animate-step-pop stagger-${index + 1} flex h-14 w-14 shrink-0 items-center justify-center text-3xl font-bold tabular-nums ${
                        activeStep === index ? "gradient-text" : "text-slate-300"
                      }`}
                    >
                      {step.number}
                    </span>
                    <div>
                      <h3 className="text-lg font-semibold text-slate-900">{step.title}</h3>
                      <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{step.description}</p>
                    </div>
                    <div className="hidden md:block">
                      <StepMockup type={step.mockupType} />
                    </div>
                  </button>
                </Fragment>
              ))}
            </div>
          </div>
        </section>

        <section id="libraries" className="relative overflow-hidden border-t border-slate-100 bg-white py-24">
          <div className="bg-svg-decor" aria-hidden="true">
            <svg viewBox="0 0 1200 500" preserveAspectRatio="xMidYMid slice">
              <defs>
                <pattern id="libDots" width="40" height="40" patternUnits="userSpaceOnUse">
                  <circle cx="20" cy="20" r="1.2" fill="#d1d5db" opacity="0.25" />
                </pattern>
              </defs>
              <rect width="1200" height="500" fill="url(#libDots)" />
              <g className="animate-drift-left" style={{ animationDuration: "15s" }}>
                <polygon points="100,60 130,80 130,120 100,140 70,120 70,80" fill="none" stroke="#e2e8f0" strokeWidth="0.8" opacity="0.35" />
              </g>
              <g className="animate-drift-right" style={{ animationDuration: "13s" }}>
                <polygon points="1080,350 1105,368 1105,404 1080,422 1055,404 1055,368" fill="none" stroke="#e2e8f0" strokeWidth="0.8" opacity="0.3" />
              </g>
              <g className="animate-spin-slow" style={{ animationDuration: "40s" }}>
                <circle cx="600" cy="250" r="100" fill="none" stroke="#f1f5f9" strokeWidth="0.5" strokeDasharray="8 12" />
              </g>
              <g className="animate-spin-reverse" style={{ animationDuration: "50s" }}>
                <circle cx="600" cy="250" r="160" fill="none" stroke="#f1f5f9" strokeWidth="0.3" strokeDasharray="4 16" />
              </g>
              <g className="animate-pulse-ring" style={{ animationDuration: "5s" }}>
                <circle cx="250" cy="400" r="45" fill="none" stroke="#e2e8f0" strokeWidth="0.5" opacity="0.3" />
              </g>
              <g className="animate-pulse-ring" style={{ animationDuration: "6s", animationDelay: "1.5s" }}>
                <circle cx="950" cy="100" r="40" fill="none" stroke="#e2e8f0" strokeWidth="0.5" opacity="0.25" />
              </g>
              <g className="animate-cross-spin" style={{ animationDuration: "7s" }}>
                <line x1="420" y1="30" x2="450" y2="60" stroke="#d1d5db" strokeWidth="1" opacity="0.3" />
                <line x1="450" y1="30" x2="420" y2="60" stroke="#d1d5db" strokeWidth="1" opacity="0.3" />
              </g>
              <g className="animate-cross-spin" style={{ animationDuration: "8s", animationDelay: "3s" }}>
                <line x1="800" y1="420" x2="830" y2="450" stroke="#d1d5db" strokeWidth="1" opacity="0.3" />
                <line x1="830" y1="420" x2="800" y2="450" stroke="#d1d5db" strokeWidth="1" opacity="0.3" />
              </g>
              {[180, 400, 650, 880].map((x, i) => (
                <g key={x} className="animate-wave-y" style={{ animationDuration: `${5 + i}s`, animationDelay: `${i * 0.6}s` }}>
                  <circle cx={x} cy={150 + (i % 2) * 200} r={2 + (i % 3)} fill="#d1d5db" opacity="0.2" />
                </g>
              ))}
              <g className="animate-fade-drift" style={{ animationDuration: "10s" }}>
                <rect x="50" y="200" width="16" height="16" rx="3" fill="none" stroke="#e2e8f0" strokeWidth="0.7" opacity="0.3" transform="rotate(45 58 208)" />
              </g>
              <g className="animate-fade-drift" style={{ animationDuration: "11s", animationDelay: "2s" }}>
                <rect x="1120" y="250" width="14" height="14" rx="3" fill="none" stroke="#e2e8f0" strokeWidth="0.7" opacity="0.3" transform="rotate(30 1127 257)" />
              </g>
            </svg>
          </div>
          <div className="mx-auto max-w-6xl px-6">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Library packs</h2>
              <p className="mt-3 text-lg text-slate-500">
                Curated rule sets for the migrations Python teams face most often.
              </p>
            </div>

            <div className="mx-auto mt-14 grid max-w-4xl grid-cols-1 gap-6 sm:grid-cols-2">
              {LIBRARIES.map((library) => {
                const Icon = library.icon;
                return (
                  <div key={library.name} className="card-hover relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-slate-50">
                          <Icon className="h-4 w-4 text-slate-700" />
                        </span>
                        <h3 className="font-mono text-sm font-semibold text-slate-900">{library.name}</h3>
                      </div>
                      <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
                        {library.rules} rules
                      </span>
                    </div>
                    <p className="mt-3 text-sm leading-relaxed text-slate-500">{library.description}</p>
                    <code className="mt-4 block truncate rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 font-mono text-xs text-slate-600">
                      $ {library.command}
                    </code>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        <section id="pricing" className="relative overflow-hidden py-24">
          <div className="bg-svg-decor" aria-hidden="true">
            <svg viewBox="0 0 1200 500" preserveAspectRatio="xMidYMid slice">
              <defs>
                <pattern id="priceLines" width="100" height="100" patternUnits="userSpaceOnUse">
                  <line x1="0" y1="50" x2="100" y2="50" stroke="#f1f5f9" strokeWidth="0.5" />
                  <line x1="50" y1="0" x2="50" y2="100" stroke="#f1f5f9" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="1200" height="500" fill="url(#priceLines)" opacity="0.5" />
              <g className="animate-drift-right" style={{ animationDuration: "14s" }}>
                <circle cx="100" cy="120" r="55" fill="none" stroke="#e2e8f0" strokeWidth="0.8" opacity="0.3" />
              </g>
              <g className="animate-drift-left" style={{ animationDuration: "12s" }}>
                <circle cx="1100" cy="380" r="50" fill="none" stroke="#e2e8f0" strokeWidth="0.8" opacity="0.25" />
              </g>
              <g className="animate-spin-slow" style={{ animationDuration: "35s" }}>
                <polygon points="600,30 640,60 640,120 600,150 560,120 560,60" fill="none" stroke="#f1f5f9" strokeWidth="0.6" opacity="0.4" />
              </g>
              <g className="animate-pulse-ring" style={{ animationDuration: "5s" }}>
                <circle cx="350" cy="420" r="40" fill="none" stroke="#e2e8f0" strokeWidth="0.5" opacity="0.3" />
              </g>
              <g className="animate-pulse-ring" style={{ animationDuration: "6s", animationDelay: "2s" }}>
                <circle cx="850" cy="80" r="35" fill="none" stroke="#e2e8f0" strokeWidth="0.5" opacity="0.25" />
              </g>
              <g className="animate-cross-spin" style={{ animationDuration: "9s" }}>
                <line x1="200" y1="60" x2="230" y2="90" stroke="#d1d5db" strokeWidth="1" opacity="0.25" />
                <line x1="230" y1="60" x2="200" y2="90" stroke="#d1d5db" strokeWidth="1" opacity="0.25" />
              </g>
              <g className="animate-cross-spin" style={{ animationDuration: "10s", animationDelay: "4s" }}>
                <line x1="980" y1="300" x2="1010" y2="330" stroke="#d1d5db" strokeWidth="1" opacity="0.25" />
                <line x1="1010" y1="300" x2="980" y2="330" stroke="#d1d5db" strokeWidth="1" opacity="0.25" />
              </g>
              {[250, 500, 750, 1000].map((x, i) => (
                <g key={x} className="animate-wave-y" style={{ animationDuration: `${4 + i * 0.8}s`, animationDelay: `${i * 0.5}s` }}>
                  <circle cx={x} cy={200 + (i % 2) * 100} r={2 + (i % 2)} fill="#d1d5db" opacity="0.2" />
                </g>
              ))}
              <g className="animate-fade-drift" style={{ animationDuration: "8s" }}>
                <rect x="70" y="350" width="20" height="20" rx="4" fill="none" stroke="#e5e7eb" strokeWidth="0.7" opacity="0.3" transform="rotate(15 80 360)" />
              </g>
              <g className="animate-fade-drift" style={{ animationDuration: "9s", animationDelay: "1s" }}>
                <rect x="1060" y="130" width="18" height="18" rx="4" fill="none" stroke="#e5e7eb" strokeWidth="0.7" opacity="0.3" transform="rotate(-25 1069 139)" />
              </g>
            </svg>
          </div>
          <div className="mx-auto max-w-6xl px-6">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Simple pricing</h2>
              <p className="mt-3 text-lg text-slate-500">Start free. Upgrade when your dependencies do.</p>
            </div>

            <div className="mx-auto mt-14 grid max-w-5xl grid-cols-1 gap-6 lg:grid-cols-3">
              {PLANS.map((plan) => (
                <div
                  key={plan.name}
                  className={`card-hover relative flex flex-col rounded-2xl bg-white p-8 ${
                    plan.highlighted ? "ring-2 ring-slate-900" : "border border-slate-200"
                  }`}
                >
                  {plan.highlighted && (
                    <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-slate-900 px-3 py-1 text-xs font-medium text-white">
                      Most popular
                    </span>
                  )}
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{plan.name}</h3>
                  <div className="mt-3 flex items-baseline gap-1">
                    <span className="text-4xl font-bold tracking-tight text-slate-900">{plan.price}</span>
                    {plan.period && <span className="text-sm text-slate-400">{plan.period}</span>}
                  </div>
                  <p className="mt-3 text-sm leading-relaxed text-slate-500">{plan.description}</p>
                  <ul className="mt-6 flex-1 space-y-3">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2.5 text-sm text-slate-600">
                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-slate-900" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <button
                    className={`btn-press mt-8 w-full rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors ${
                      plan.highlighted
                        ? "bg-slate-900 text-white hover:bg-slate-800"
                        : "border border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                    }`}
                  >
                    {plan.cta}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="pb-24">
          <div className="mx-auto max-w-5xl px-6">
            <div className="relative overflow-hidden rounded-3xl bg-slate-900 px-8 py-14 text-center md:p-16">
              <div className="pointer-events-none absolute inset-0">
                <svg viewBox="0 0 1200 500" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
                  <defs>
                    <pattern id="ctaDots" width="50" height="50" patternUnits="userSpaceOnUse">
                      <circle cx="25" cy="25" r="0.8" fill="white" opacity="0.08" />
                    </pattern>
                  </defs>
                  <rect width="1200" height="500" fill="url(#ctaDots)" />
                  <g className="animate-drift-left" style={{ animationDuration: "15s" }}>
                    <circle cx="150" cy="80" r="60" fill="none" stroke="white" strokeWidth="0.5" opacity="0.08" />
                    <circle cx="150" cy="80" r="90" fill="none" stroke="white" strokeWidth="0.3" opacity="0.05" />
                  </g>
                  <g className="animate-drift-right" style={{ animationDuration: "18s" }}>
                    <circle cx="1050" cy="400" r="50" fill="none" stroke="white" strokeWidth="0.5" opacity="0.07" />
                    <circle cx="1050" cy="400" r="80" fill="none" stroke="white" strokeWidth="0.3" opacity="0.04" />
                  </g>
                  <g className="animate-spin-slow" style={{ animationDuration: "45s" }}>
                    <polygon points="600,20 650,55 650,125 600,160 550,125 550,55" fill="none" stroke="white" strokeWidth="0.4" opacity="0.06" />
                  </g>
                  <g className="animate-pulse-ring" style={{ animationDuration: "6s" }}>
                    <circle cx="350" cy="250" r="70" fill="none" stroke="white" strokeWidth="0.3" opacity="0.06" />
                  </g>
                  <g className="animate-pulse-ring" style={{ animationDuration: "7s", animationDelay: "2s" }}>
                    <circle cx="850" cy="180" r="55" fill="none" stroke="white" strokeWidth="0.3" opacity="0.05" />
                  </g>
                  {[200, 400, 600, 800, 1000].map((x, i) => (
                    <g key={x} className="animate-wave-y" style={{ animationDuration: `${4 + i * 0.6}s`, animationDelay: `${i * 0.3}s` }}>
                      <circle cx={x} cy={100 + (i % 3) * 120} r={1.5 + (i % 2)} fill="white" opacity="0.06" />
                    </g>
                  ))}
                  <g className="animate-cross-spin" style={{ animationDuration: "10s" }}>
                    <line x1="100" y1="300" x2="130" y2="330" stroke="white" strokeWidth="0.5" opacity="0.06" />
                    <line x1="130" y1="300" x2="100" y2="330" stroke="white" strokeWidth="0.5" opacity="0.06" />
                  </g>
                  <g className="animate-cross-spin" style={{ animationDuration: "11s", animationDelay: "3s" }}>
                    <line x1="1080" y1="100" x2="1110" y2="130" stroke="white" strokeWidth="0.5" opacity="0.06" />
                    <line x1="1110" y1="100" x2="1080" y2="130" stroke="white" strokeWidth="0.5" opacity="0.06" />
                  </g>
                </svg>
              </div>
              <h2 className="text-3xl font-bold tracking-tight text-white md:text-4xl">Ready to migrate?</h2>
              <p className="mx-auto mt-3 max-w-md text-base text-slate-400">
                Install a pack, point it at your repo, review the diff and ship it.
              </p>
              <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <a
                  href={user ? "/dashboard" : "/auth/register"}
                  className="btn-press inline-flex items-center gap-2 rounded-xl bg-white px-6 py-3 text-sm font-semibold text-slate-900 transition-colors hover:bg-slate-100"
                >
                  Get started free
                  <ArrowRight className="h-4 w-4" />
                </a>
                <a
                  href="#how"
                  className="btn-press inline-flex items-center gap-2 rounded-xl border border-white/20 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-white/10"
                >
                  See how it works
                </a>
              </div>

              <div className="mx-auto mt-10 max-w-3xl">
                <p className="mb-3 text-left text-sm font-mono text-white/50">requests v1.0 → v2.0</p>
                <div className="vehicle-track">
                  <svg viewBox="0 0 1200 140" className="w-full" style={{ overflow: "visible" }}>
                    <path
                      d={VEHICLE_PATH}
                      fill="none"
                      stroke="rgba(255,255,255,0.12)"
                      strokeWidth="2"
                      strokeDasharray="8 6"
                    />
                    {VERSION_NODES.map((node) => (
                      <g key={node.label}>
                        <circle
                          cx={node.x}
                          cy={node.y}
                          r={node.major ? 7 : 5}
                          fill={node.major ? "#ffffff" : "rgba(255,255,255,0.7)"}
                        />
                        <text
                          x={node.x}
                          y={node.y + (node.y > 50 ? 24 : -14)}
                          textAnchor="middle"
                          fontSize="13"
                          fontFamily="JetBrains Mono, monospace"
                          fill={node.major ? "rgba(255,255,255,0.85)" : "rgba(255,255,255,0.6)"}
                        >
                          {node.label}
                        </text>
                      </g>
                    ))}
                    <g>
                      <animateMotion
                        dur="5s"
                        repeatCount="indefinite"
                        rotate="auto"
                        path={VEHICLE_PATH}
                      />
                      <rect x="-22" y="-12" width="40" height="20" rx="4" fill="#ffffff" />
                      <rect x="-19" y="-9" width="11" height="8" rx="1.5" fill="#e2e8f0" />
                      <rect x="-5" y="-9" width="11" height="8" rx="1.5" fill="#e2e8f0" />
                      <rect x="16" y="-6" width="10" height="14" rx="2" fill="#f1f5f9" />
                      <circle cx="-12" cy="10" r="4" fill="#1e293b" stroke="#94a3b8" strokeWidth="1" />
                      <circle cx="12" cy="10" r="4" fill="#1e293b" stroke="#94a3b8" strokeWidth="1" />
                    </g>
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="relative overflow-hidden border-t border-slate-200 py-10">
        <div className="bg-svg-decor" aria-hidden="true">
          <svg viewBox="0 0 1200 100" preserveAspectRatio="xMidYMid slice">
            <defs>
              <pattern id="footerDots" width="30" height="30" patternUnits="userSpaceOnUse">
                <circle cx="15" cy="15" r="0.6" fill="#d1d5db" opacity="0.3" />
              </pattern>
            </defs>
            <rect width="1200" height="100" fill="url(#footerDots)" />
            <g className="animate-wave-y" style={{ animationDuration: "6s" }}>
              <circle cx="200" cy="50" r="1.5" fill="#d1d5db" opacity="0.3" />
            </g>
            <g className="animate-wave-y" style={{ animationDuration: "7s", animationDelay: "1s" }}>
              <circle cx="600" cy="40" r="1.5" fill="#d1d5db" opacity="0.25" />
            </g>
            <g className="animate-wave-y" style={{ animationDuration: "5s", animationDelay: "2s" }}>
              <circle cx="1000" cy="60" r="1.5" fill="#d1d5db" opacity="0.3" />
            </g>
          </svg>
        </div>
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 px-6 sm:flex-row">
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-900">
              <Zap className="h-3.5 w-3.5 text-white" fill="currentColor" />
            </span>
            <span className="text-sm text-slate-500">© 2026 MigratorGen. All rights reserved.</span>
          </div>
          <nav className="flex items-center gap-6 text-sm text-slate-500">
            <a href={user ? "/dashboard" : "/auth/login"} className="transition-colors hover:text-slate-900">Dashboard</a>
            <a href="#libraries" className="transition-colors hover:text-slate-900">Libraries</a>
            <a href="#" className="transition-colors hover:text-slate-900">GitHub</a>
          </nav>
        </div>
      </footer>
    </div>
  );
}
