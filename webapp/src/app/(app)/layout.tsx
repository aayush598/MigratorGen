"use client";

import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useState, useEffect, useCallback, type ReactNode } from "react";
import { useSession, signOut } from "@/lib/auth-client";
import { Toaster } from "@/components/ui/toaster";
import { hydrateMigrationStore } from "@/stores/migration-store";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/migrations", label: "Migrations" },
  { href: "/libraries", label: "Libraries" },
  { href: "/rules", label: "Rules" },
  { href: "/api-keys", label: "API Keys" },
  { href: "/settings", label: "Settings" },
  { href: "/billing", label: "Billing" },
];

// Module-level browser-like history for the back/forward buttons
const HISTORY: string[] = [];
let HISTORY_INDEX = -1;
let IS_HISTORY_NAV = false;

function NavIcon({ name }: { name: string }) {
  const paths: Record<string, string[]> = {
    Dashboard: [
      "M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25",
    ],
    Migrations: [
      "M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182",
    ],
    Libraries: [
      "M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z",
    ],
    Rules: [
      "M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z",
    ],
    "API Keys": [
      "M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z",
    ],
    Settings: [
      "M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z",
      "M15 12a3 3 0 11-6 0 3 3 0 016 0z",
    ],
    Billing: [
      "M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5z",
    ],
  };

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="h-[18px] w-[18px] shrink-0"
    >
      {(paths[name] ?? []).map((d) => (
        <path
          key={d}
          strokeLinecap="round"
          strokeLinejoin="round"
          d={d}
        />
      ))}
    </svg>
  );
}

export default function AppLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session } = useSession();

  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [historyState, setHistoryState] = useState({ index: -1, length: 0 });

  // Hydration + restore persisted sidebar state
  useEffect(() => {
    setMounted(true);
    hydrateMigrationStore();
    try {
      const stored = window.localStorage.getItem("mg_sidebar_collapsed");
      if (stored === "true") setCollapsed(true);
    } catch {
      // localStorage unavailable
    }
  }, []);

  // Track navigation history + close mobile drawer on route change
  useEffect(() => {
    if (IS_HISTORY_NAV) {
      IS_HISTORY_NAV = false;
      setHistoryState({ index: HISTORY_INDEX, length: HISTORY.length });
    } else if (HISTORY[HISTORY_INDEX] !== pathname) {
      HISTORY.splice(HISTORY_INDEX + 1);
      HISTORY.push(pathname);
      HISTORY_INDEX = HISTORY.length - 1;
      setHistoryState({ index: HISTORY_INDEX, length: HISTORY.length });
    }
    setMobileOpen(false);
  }, [pathname]);

  const handleBack = useCallback(() => {
    if (HISTORY_INDEX <= 0) return;
    HISTORY_INDEX -= 1;
    IS_HISTORY_NAV = true;
    router.push(HISTORY[HISTORY_INDEX]);
  }, [router]);

  const handleForward = useCallback(() => {
    if (HISTORY_INDEX >= HISTORY.length - 1) return;
    HISTORY_INDEX += 1;
    IS_HISTORY_NAV = true;
    router.push(HISTORY[HISTORY_INDEX]);
  }, [router]);

  const canBack = historyState.index > 0;
  const canForward = historyState.index >= 0 && historyState.index < historyState.length - 1;

  const isActive = useCallback(
    (href: string) => pathname === href || pathname.startsWith(href + "/"),
    [pathname]
  );

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem("mg_sidebar_collapsed", String(next));
      } catch {
        // localStorage unavailable
      }
      return next;
    });
  }, []);

  const handleSignOut = async () => {
    await signOut();
    router.push("/auth/login");
  };

  // Breadcrumbs derived from the current pathname
  const segments = pathname.split("/").filter(Boolean);
  const navLabelFor = (seg: string) =>
    NAV.find((item) => item.href === `/${seg}`)?.label ?? null;

  const breadcrumbs = [
    ...segments.map((seg, i) => {
      const label = navLabelFor(seg) ?? seg.replace(/-/g, " ");
      return {
        label: label.charAt(0).toUpperCase() + label.slice(1),
        href: "/" + segments.slice(0, i + 1).join("/"),
      };
    }),
  ];

  const email = session?.user?.email ?? "";
  const avatarLetter = email ? email.charAt(0).toUpperCase() : "?";

  const renderNavLinks = (isCollapsed: boolean) => (
    <nav className={`flex flex-1 flex-col gap-1 ${isCollapsed ? "items-center px-2" : "px-3"}`}>
      {NAV.map((item) => {
        const active = isActive(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            title={isCollapsed ? item.label : undefined}
            className={`btn-press flex items-center rounded-xl text-sm font-medium transition-colors ${
              isCollapsed ? "justify-center px-0 py-2.5" : "gap-3 px-3 py-2.5"
            } ${
              active
                ? "bg-slate-100 text-slate-900"
                : "text-slate-500 hover:bg-slate-50 hover:text-slate-700"
            }`}
          >
            <NavIcon name={item.label} />
            {!isCollapsed && <span className="text-[13px]">{item.label}</span>}
          </Link>
        );
      })}
    </nav>
  );

  const renderLogo = (isCollapsed: boolean) => (
      <Link
      href="/dashboard"
      className={`flex items-center gap-3 px-5 pb-4 pt-6 ${isCollapsed ? "justify-center px-0" : ""}`}
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={2}
          stroke="currentColor"
          className="h-4 w-4 text-white"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
          />
        </svg>
      </div>
      {!isCollapsed && (
        <span className="text-sm font-semibold tracking-tight text-slate-900">MigratorGen</span>
      )}
    </Link>
  );

  const renderUserSection = (isCollapsed: boolean) => (
    <div className={`border-t border-slate-100 px-3 py-3 ${isCollapsed ? "flex flex-col items-center gap-2" : ""}`}>
      {mounted && session?.user ? (
        <div className={`flex items-center ${isCollapsed ? "justify-center" : "gap-3 px-1"} py-1`}>
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-200 text-[11px] font-semibold text-slate-600">
            {avatarLetter}
          </div>
          {!isCollapsed && (
            <span className="min-w-0 truncate text-xs text-slate-400">{email}</span>
          )}
        </div>
      ) : (
        <div className={`flex items-center ${isCollapsed ? "justify-center" : "gap-3 px-1"} py-1`}>
          <div className="skeleton h-7 w-7 shrink-0 rounded-full" />
          {!isCollapsed && <div className="skeleton h-3 w-28" />}
        </div>
      )}
      <button
        onClick={handleSignOut}
        title="Sign out"
        className={`btn-press flex w-full items-center rounded-xl text-sm font-medium text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600 ${
          isCollapsed ? "justify-center px-0 py-2.5" : "gap-3 px-3 py-2.5"
        }`}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="h-[18px] w-[18px] shrink-0"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9"
          />
        </svg>
        {!isCollapsed && <span>Sign out</span>}
      </button>
    </div>
  );

  const renderCollapseToggle = () => (
    <button
      onClick={toggleCollapsed}
      title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      className="btn-press mb-3 flex w-full items-center justify-center border-t border-slate-100 pt-3 text-slate-500 transition-colors hover:text-slate-900"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
        stroke="currentColor"
        className="h-5 w-5"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d={collapsed ? "M8.25 4.5l7.5 7.5-7.5 7.5" : "M15.75 19.5L8.25 12l7.5-7.5"} />
      </svg>
    </button>
  );

  return (
    <div className="flex h-screen bg-[#fafafa]">
      {/* Desktop sidebar */}
      <aside
        style={{ width: collapsed ? 72 : 260 }}
        className="hidden shrink-0 flex-col border-r border-slate-200 bg-white transition-all duration-200 ease-in-out lg:flex"
      >
        {renderLogo(collapsed)}
        {renderNavLinks(collapsed)}
        {renderUserSection(collapsed)}
        {renderCollapseToggle()}
      </aside>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="animate-fade-in absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="animate-slide-in absolute left-0 top-0 flex h-full w-[260px] flex-col border-r border-slate-200 bg-white shadow-xl">
            <button
              onClick={() => setMobileOpen(false)}
              aria-label="Close menu"
              className="absolute right-3 top-4 btn-press rounded-xl p-2 text-slate-400 hover:bg-slate-50 hover:text-slate-600"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="h-5 w-5"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            {renderLogo(false)}
            {renderNavLinks(false)}
            {renderUserSection(false)}
          </aside>
        </div>
      )}

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Header bar */}
        <header className="sticky top-0 z-40 flex h-[52px] shrink-0 items-center gap-2 border-b border-slate-100 bg-white/80 px-4 backdrop-blur-md lg:px-6">
          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
            className="btn-press rounded-xl p-2 text-slate-400 hover:bg-slate-50 lg:hidden"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="h-5 w-5"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>

          {/* Back / forward */}
          <div className="flex items-center gap-1">
            <button
              onClick={handleBack}
              disabled={!canBack}
              title="Back"
              aria-label="Go back"
              className="btn-press rounded-xl p-2 text-slate-400 hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-30"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="h-4 w-4"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
              </svg>
            </button>
            <button
              onClick={handleForward}
              disabled={!canForward}
              title="Forward"
              aria-label="Go forward"
              className="btn-press rounded-xl p-2 text-slate-400 hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-30"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="h-4 w-4"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </button>
          </div>

          {/* Breadcrumbs */}
          <nav className="ml-1 flex min-w-0 items-center gap-1.5 text-sm" aria-label="Breadcrumb">
            {breadcrumbs.length === 0 ? (
              <span className="font-medium text-slate-400">Home</span>
            ) : (
              breadcrumbs.map((crumb, i) => {
                const isLast = i === breadcrumbs.length - 1;
                return (
                  <span key={crumb.href} className="flex min-w-0 items-center gap-1.5">
                    {i > 0 && (
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={1.5}
                        stroke="currentColor"
                        className="h-3.5 w-3.5 shrink-0 text-slate-400"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                      </svg>
                    )}
                    {isLast ? (
                      <span className="truncate font-medium text-slate-600">{crumb.label}</span>
                    ) : (
                      <Link
                        href={crumb.href}
                        className="truncate text-slate-500 transition-colors hover:text-slate-900"
                      >
                        {crumb.label}
                      </Link>
                    )}
                  </span>
                );
              })
            )}
          </nav>
        </header>

        {/* Content area */}
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1200px] px-6 py-8 lg:px-10">{children}</div>
        </main>
      </div>
      <Toaster />
    </div>
  );
}
