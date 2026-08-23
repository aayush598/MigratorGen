"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { resetPassword } from "@/lib/auth-client";
import { resetPasswordSchema, type ResetPasswordInput } from "@/schemas";
import { Button } from "@/components/ui/button";
import { Input, Label, FieldError } from "@/components/ui/input";
import { CheckCircle2, Lock } from "lucide-react";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [done, setDone] = useState(false);

  const form = useForm<ResetPasswordInput>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "", confirmPassword: "" },
  });

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#fafafa] px-6">
        <div className="w-full max-w-sm text-center">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-600">Invalid or missing reset token.</p>
            <Link href="/auth/forgot-password" className="mt-3 inline-block text-xs font-medium text-slate-700 hover:text-slate-900">
              Request a new link
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const onSubmit = async (data: ResetPasswordInput) => {
    try {
      const res = await resetPassword(data.password, token);
      if (res.error) {
        form.setError("root", { message: res.error.message || "Reset failed" });
      } else {
        setDone(true);
        setTimeout(() => router.push("/auth/login"), 2000);
      }
    } catch {
      form.setError("root", { message: "Reset failed" });
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#fafafa] px-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <Link href="/" className="mb-6 inline-flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900">
              <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
              </svg>
            </span>
            <span className="text-lg font-semibold text-slate-900">MigratorGen</span>
          </Link>
          <h1 className="text-2xl font-bold text-slate-900">Set new password</h1>
          <p className="mt-1 text-sm text-slate-500">Choose a strong password for your account</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          {done ? (
            <div className="flex flex-col items-center gap-3 py-4 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50">
                <CheckCircle2 className="h-6 w-6 text-emerald-500" />
              </div>
              <p className="text-sm font-medium text-slate-900">Password updated</p>
              <p className="text-xs text-slate-500">Redirecting you to sign in...</p>
            </div>
          ) : (
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <Label htmlFor="password">New password</Label>
                <Input id="password" type="password" placeholder="At least 8 characters" autoComplete="new-password" {...form.register("password")} />
                <FieldError message={form.formState.errors.password?.message} />
              </div>
              <div>
                <Label htmlFor="confirmPassword">Confirm password</Label>
                <Input id="confirmPassword" type="password" placeholder="Repeat your password" autoComplete="new-password" {...form.register("confirmPassword")} />
                <FieldError message={form.formState.errors.confirmPassword?.message} />
              </div>
              {form.formState.errors.root && (
                <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{form.formState.errors.root.message}</p>
              )}
              <Button type="submit" className="w-full" loading={form.formState.isSubmitting}>
                <Lock className="mr-2 h-4 w-4" />
                Reset password
              </Button>
            </form>
          )}

          <p className="mt-5 text-center text-xs text-slate-400">
            <Link href="/auth/login" className="font-medium text-slate-700 transition-colors hover:text-slate-900">
              Back to sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}
