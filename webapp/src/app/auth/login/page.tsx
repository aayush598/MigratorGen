"use client";

import { SignIn } from "@clerk/nextjs";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#fafafa] px-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <a href="/" className="mb-6 inline-flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900">
              <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
              </svg>
            </span>
            <span className="text-lg font-semibold text-slate-900">MigratorGen</span>
          </a>
          <h1 className="text-2xl font-bold text-slate-900">Welcome back</h1>
          <p className="mt-1 text-sm text-slate-500">Sign in to your account</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <SignIn
            routing="path"
            path="/auth/login"
            appearance={{
              elements: {
                rootBox: "w-full",
                card: "shadow-none border-0 w-full",
                formButtonPrimary: "bg-slate-900 hover:bg-slate-800 text-white",
                footerActionLink: "text-slate-600 hover:text-slate-900",
                formFieldInput: "rounded-xl border-slate-200",
                headerTitle: "text-slate-900",
                headerSubtitle: "text-slate-500",
              },
            }}
          />
        </div>
      </div>
    </div>
  );
}
