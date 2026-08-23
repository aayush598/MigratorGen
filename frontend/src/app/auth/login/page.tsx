"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { signIn } from "@/lib/auth-client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { error: signInError } = await signIn.email({
        email,
        password,
      });
      if (signInError) {
        setError(signInError.message || "Invalid credentials");
      } else {
        router.push("/dashboard");
      }
    } catch {
      setError("Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mesh-gradient min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2.5 mb-6">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
              <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
              </svg>
            </span>
            <span className="text-lg font-semibold text-zinc-100">MigratorGen</span>
          </Link>
          <h1 className="text-2xl font-bold text-zinc-100">Welcome back</h1>
          <p className="text-sm text-zinc-500 mt-1">Sign in to your account</p>
        </div>

        <div className="bg-[#18181b] rounded-xl border border-white/10 p-6">
          {error && (
            <div className="mb-4 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2 text-sm text-red-400">
              {error}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[13px] font-medium text-zinc-400 mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#09090b] border border-white/10 rounded-lg text-[13px] text-zinc-100 placeholder-zinc-600 focus:ring-1 focus:ring-blue-500/30 focus:border-blue-500 outline-none transition-all"
                required
              />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-zinc-400 mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-[#09090b] border border-white/10 rounded-lg text-[13px] text-zinc-100 placeholder-zinc-600 focus:ring-1 focus:ring-blue-500/30 focus:border-blue-500 outline-none transition-all"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-[13px] font-semibold hover:bg-blue-700 disabled:opacity-50 transition-all btn-press"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </div>

        <p className="mt-4 text-center text-[13px] text-zinc-500">
          Don&apos;t have an account?{" "}
          <Link href="/auth/register" className="text-blue-400 hover:text-blue-300 font-medium transition-colors">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
